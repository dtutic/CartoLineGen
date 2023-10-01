# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CartoLineGen
                                 A QGIS plugin
 Simplify and smooth lines for given map scale.
                              -------------------
        begin                : 2016-05-25
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Dražen Tutić
        email                : dtutic@north2south.eu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
try:
    from osgeo import ogr
except ImportError:
    import ogr
    
import sys,math,random,os
import numpy as np
from PyQt5.QtWidgets import QProgressBar


def initialize():
    global progressbar
    progressbar = QProgressBar()


def zig_zag(a,b,c,d): #returns true if three segments form zig-zag
    return (a[1]*(c[0]-b[0])+b[1]*(a[0]-c[0])+c[1]*(b[0]-a[0]))*(b[1]*(d[0]-c[0])+c[1]*(b[0]-d[0])+d[1]*(c[0]-b[0])) < -ZERO_EPSILON

def polygon_area(a,b,c,d): #surveyors formula for 4 points
    return (b[0]-a[0])*(b[1]+a[1])+(c[0]-b[0])*(c[1]+b[1])+(d[0]-c[0])*(d[1]+c[1]) 

def polygon_area_closed(a,b,c,d): #surveyors formula for 4 points
    return a[0]*(b[1]-d[1])+b[0]*(c[1]-a[1])+c[0]*(d[1]-b[1])+d[0]*(a[1]-c[1])

def squared_length(p1,p2): #squared length of segment
    return (p1[0]-p2[0])*(p1[0]-p2[0])+(p1[1]-p2[1])*(p1[1]-p2[1])   

def segments_angle(p1, p2, p3): 
    a1 = math.atan2(p1[1]-p2[1], p1[0]-p2[0])
    a2 = math.atan2(p3[1]-p2[1], p3[0]-p2[0]) #angles from middle point to first and third point
    if (a1 < 0.):
        a1 += 2.*math.pi
    if (a2 < 0.): 
        a2 += 2.*math.pi #if angles are negative correct then to 0-2PI interval
    if (a1 > a2): 
        da = a1 - a2
    else:
        da = a2 - a1 # subtract smaller angle from larger angle
    if (da > math.pi):
        da = math.pi*2. - da; # correct the angle to interval 0-PI
    return da

    

#------------------------------------------------------------------------------------------------------------------
# Main simplification function for orthogonal segments
# Takes four consecutive points forming three consecutive and perpendicular segments in line
# Segments forms "S" shape, zig-zag line because this is part of line that is usefull to simplify. For example,
# convex part of lines will be intact, as well as convex shapes.
# Vertices p1 and p4 are replaced by new points pA and PB in a way that
# area of input and output figure is preserved, and p2 and p3 is deleted.
#
# TODO: Preserve area when near orthogonal segments exists
#------------------------------------------------------------------------------------------------------------------ 
    
def Simplify_Ortho(p1,p2,p3,p4): 
    pA = np.zeros(2)
    pB = np.zeros(2)
    
    d12 = math.sqrt(squared_length(p1,p2))
    d23 = math.sqrt(squared_length(p2,p3))
    d34 = math.sqrt(squared_length(p3,p4))
    
    dB = d12*d23/(d34+d12)
    dA = d23 - dB
    
    v1A = math.atan2(p3[1]-p2[1],p3[0]-p2[0])
    v4B = math.atan2(p2[1]-p3[1],p2[0]-p3[0])
    
    pA[0] = p1[0] + dA*math.cos(v1A)
    pA[1] = p1[1] + dA*math.sin(v1A)
    pB[0] = p4[0] + dB*math.cos(v4B)
    pB[1] = p4[1] + dB*math.sin(v4B) 
       
    return 1,pA,pB
    
#-----------------------------------------------------------------------------------------------------------------
# This functions simplifies lines with orthogonal segments. First and last points are same in output which preserves topology.
# Local operator in function Simplify_Ortho is called first for the smallest segment in line which forms zig-zig with
# its neighbouring segments, and after modification, the smallest segment in modified line is next candidate for
# simplification.
# This way line is almost always treated in the same order (exception can be multiple segments with minimal length)
# and this is very useful for generalisation of duplicate lines, because such borders will remain very close, or
# equal on some parts. Other advantage is that it gives kind of global property to generalisation, meaning that
# line can be generalised multiple times through intermediate scales or directly to final smaller scale, and result 
# should be same or very similar.
#------------------------------------------------------------------------------------------------------------------  
    
def Simplify_Line_Ortho(g,closed,geom_type):
    if closed:
        input_area = g.Area()
        if input_area < DEL_AREA:
            return 0,g #area of ring is too small to keep on map   
            
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] or points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list
    
    #malformed linear geometry
    if p_len <= 1:
        return 0,g
    #segment or two segments, nothing to generalize, return cleaned geometry    
    if p_len <= 3:
        line = ogr.Geometry(ogr.wkbLineString)    
        for i in range (0,p_len):
            line.AddPoint(points[i,0], points[i,1])
        return -1,line
        
    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i], points[i+1])
    i = np.argmin(segments) #index of shorthest segment
    min_s = np.amin(segments) #squared length of shorthest segment
    while min_s < SQR_TOL_LENGTH and p_len > 3:  
        if i > 0 and i < p_len-2: #we are not on first or last segment
          if zig_zag(points[i-1],points[i],points[i+1],points[i+2]) and math.fabs(segments_angle(points[i-1],points[i],points[i+1])-math.pi*0.5) < math.pi*0.03 and math.fabs(segments_angle(points[i],points[i+1],points[i+2])-math.pi*0.5) < math.pi*0.03: #segments should be close to orthogonal +-5°
            flag,pA,pB = Simplify_Ortho(points[i-1],points[i],points[i+1],points[i+2])
            if flag == 1:
                points[i-1] = pA
                if closed and i == 1:
                  points[p_len-1] = pA 
                points[i+2] = pB
                if closed and (i + 2 == p_len - 1):
                  points[0] = pB 
                points = np.delete(points,i+1,0)
                points = np.delete(points,i,0)
                segments = np.delete(segments,i)
                segments = np.delete(segments,i)
                p_len = p_len - 2
                #calculate new segments length with new points
                segments[i-1] = squared_length(pA, pB)
                #recalculate neigbour segments in case they were set to 2*SQR_TOL_LENGTH
                #check if close to starting/ending point of closed polyline
                if i == 1 and p_len > 2:
                    segments[i] = squared_length(points[i], points[i+1])
                elif i == p_len-3 and p_len > 2:
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                elif i > 1 and i < p_len-1 and p_len > 3:  
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                    segments[i] = squared_length(points[i], points[i+1])
          else:
            segments[i] = 2*SQR_TOL_LENGTH
        else:
          segments[i] = 2*SQR_TOL_LENGTH
        i = np.argmin(segments) #index of new shortest segment
        min_s = np.amin(segments) #squared length of new shortest segment
        
    line = ogr.Geometry(ogr.wkbLineString)    
    if closed and geom_type == 0:
        line = ogr.Geometry(ogr.wkbLinearRing)    
    for i in range (0,p_len):
      line.AddPoint(points[i,0], points[i,1])
        
    return 1,line
    
    
#------------------------------------------------------------------------------------------------------------------
# Main simplification function
# Takes four consecutive points forming three consecutive segments in line
# Segments forms "S" shape, zig-zag line because this is part of line that is usefull to simplify. For example,
# convex part of lines will be intact, as well as convex shapes.
# Algorithm preserves p1 and p4. Vertices p2 and p3 are replaces by now point pt in a way that
# area of input and output figure is preserved, and area of intersection of figures
# p1-p2-p3-p4-p1 and p1-pt-p4-p1 is maximal. This way closenes of input and output lines is
# reasonable and nicely preserved.
#
# TODO: This is fairly complicated computation for each deleted point and performance should be improved
#------------------------------------------------------------------------------------------------------------------ 
    
def Simplify(p1,p2,p3,p4): # chose new point so that the area of intersection of input and output figure is maximal
    pt = np.zeros(2)
    C1 = p2[0]*(p1[1]-p3[1])+p3[0]*(p2[1]-p4[1])-p1[0]*p2[1]+p4[0]*p3[1]
    A1 = p1[1] - p4[1]
    B1 = p4[0] - p1[0]
    A2 = p2[1] - p1[1]
    B2 = p1[0] - p2[0]
    C2 = A2*p1[0] + B2*p1[1]
    c = A1*B2 - A2*B1
    if c != 0.:
        pt[0] = (B2*C1 - B1*C2)/c
        pt[1] = (A1*C2 - A2*C1)/c
        if (pt[0]-p1[0])*(pt[0]-p2[0]) > 0. or (pt[1]-p1[1])*(pt[1]-p2[1]) > 0.: 
            A2 = p4[1]-p3[1]
            B2 = p3[0]-p4[0]
            C2 = A2*p3[0]+B2*p3[1]
            c = A1*B2-A2*B1
            if (c!=0.):
                pt[0] = (B2*C1-B1*C2)/c
                pt[1] = (A1*C2-A2*C1)/c
                if (pt[0]-p3[0])*(pt[0]-p4[0]) > 0. or (pt[1]-p3[1])*(pt[1]-p4[1]) > 0.: 
                    pt[0] = (p1[0]+p4[0])*0.5
                    pt[1] = (p1[1]+p4[1])*0.5
    else:
        A2 = p4[1]-p3[1]
        B2 = p3[0]-p4[0]
        C2 = A2*p3[0]+B2*p3[1]
        c = A1*B2-A2*B1
        if (c!=0.):
            pt[0] = (B2*C1-B1*C2)/c
            pt[1] = (A1*C2-A2*C1)/c
            if (pt[0]-p3[0])*(pt[0]-p4[0]) > 0. or (pt[1]-p3[1])*(pt[1]-p4[1]) > 0.: 
                pt[0] = (p1[0]+p4[0])*0.5
                pt[1] = (p1[1]+p4[1])*0.5
        else:
            if abs(polygon_area_closed(p1,p2,p3,p4)) < ZERO_EPSILON:
                pt[0] = (p1[0]+p4[0])*0.5
                pt[1] = (p1[1]+p4[1])*0.5
    return 1,pt
    
#-----------------------------------------------------------------------------------------------------------------
# This functions simplifies closed lines (rings). 
# Closed lines are treated in a way that no point is considered as starting or ending point and each point
# can be deleted or moved. This gives better output, as the line is redrawed manually.
# Local operator in function Simplify is called first for the smallest segment in line which forms zig-zig with
# its neighbouring segments, and after modification, the smallest segment in modified line is next candidate for
# simplification.
# This way line is almost always treated in the same order (exception can be multiple segments with minimal length)
# and this is very useful for generalisation of neighbouring polygons, because borders will remain very close, or
# equal on some parts. Other advantage is that it gives kind of global property to generalisation, meaning that
# line can be generalised multiple times through intermediate scales or directly to final smaller scale, and result 
# should be same or very similar.
#------------------------------------------------------------------------------------------------------------------
 
def Simplify_Ring(g,geom_type):
    input_area = g.Area()
    if input_area < DEL_AREA:
        return 0,g #area of ring is too small to keep on map   
   
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] or points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list
    
    #malformed closed geometry
    if p_len < 4:
        return 0,g
    #triangle, nothing to generalize, return cleaned    
    if p_len == 4:    
        if geom_type == 0:
            ring = ogr.Geometry(ogr.wkbLinearRing)    
        else:
            ring = ogr.Geometry(ogr.wkbLineString)    
        for i in range (0,p_len):
            ring.AddPoint(points[i,0], points[i,1])
        if points[0,0]!=points[p_len-1,0] or points[0,1]!=points[p_len-1,1]:
            ring.AddPoint(points[0,0], points[0,1])
        return -1,ring

    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i],points[i+1])
           
    i = np.argmin(segments) #index of shorthest segment
    min_s = np.amin(segments) #squared length of shorthest segment
    while min_s < SQR_TOL_LENGTH and p_len > 4:            
        if i == 0: #modify last, first and second segment in closed polyline       
          if zig_zag(points[p_len-2],points[0],points[1],points[2]): #part of line is zig-zag, simplify
            flag,point = Simplify(points[p_len-2],points[0],points[1],points[2])
            if flag == 1:
                points[0] = point #set new value of starting point
                points[p_len-1] = point #set new value of ending point = starting point
                points = np.delete(points,1,0) #delete extra point, by this simplification is achieved
                segments = np.delete(segments,i) #delete extra segment, by this simplification is achieved
                p_len = p_len - 1 #set new points count
                #calculate new segments lengths with new point
                segments[p_len-2] = squared_length(points[p_len-2], points[i])
                segments[i] = squared_length(points[i], points[i+1])
                #recalculate neigbour segments in case they were set to 2*SQR_TOL_LENGTH
                segments[1] = squared_length(points[1], points[2])
                segments[p_len-2] = squared_length(points[p_len-2], points[p_len-1])
          else:
            segments[i] = 2*SQR_TOL_LENGTH #part of line is not zig-zag, set segment length>SQR_TOL_LENGTH in order to avoid it in next iteration
        elif i == p_len-2: #modify before last, last and first segment
          if zig_zag(points[i-1],points[i],points[i+1],points[1]):
            flag,point = Simplify(points[i-1],points[i],points[i+1],points[1])
            if flag == 1:
                points[i] = point #set new value of ending point
                points[0] = point #set new value of starting point = ending point
                points = np.delete(points,i+1,0)
                segments = np.delete(segments,i)
                p_len = p_len - 1
                #calculate new segments lengths with new point
                segments[i-1] = squared_length(points[i-1], points[i])
                segments[0] = squared_length(points[0], points[1])
                #recalculate neigbour segments in case they were set to 2*SQR_TOL_LENGTH
                segments[1] = squared_length(points[1], points[2])
                segments[i-2] = squared_length(points[i-2], points[i-1])
          else:
            segments[i] = 2*SQR_TOL_LENGTH
        else: #we are somewhere in the "middle" of line, neighbouring points do not cross starting point of closed polyline
          if zig_zag(points[i-1],points[i],points[i+1],points[i+2]):
            flag,point = Simplify(points[i-1],points[i],points[i+1],points[i+2])
            if flag == 1:
                points[i] = point
                points = np.delete(points,i+1,0)
                segments = np.delete(segments,i)
                p_len = p_len - 1
                #calculate new segments lengths with new point
                segments[i-1] = squared_length(points[i-1], points[i])
                segments[i] = squared_length(points[i], points[i+1])
                #recalculate neigbour segments in case they were set to 2*SQR_TOL_LENGTH
                #check if close to starting/ending point of closed polyline
                if i == 1:
                    segments[p_len-2] = squared_length(points[p_len-2], points[i-1])
                    segments[i+1] = squared_length(points[i+1], points[i+2])
                elif i == p_len-2:
                    segments[0] = squared_length(points[0], points[1])
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                else:  
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                    segments[i+1] = squared_length(points[i+1], points[i+2])
          else:
            segments[i] = 2*SQR_TOL_LENGTH
        i = np.argmin(segments) #index of new shortest segment
        min_s = np.amin(segments) #squared length of new shortest segment
        
    if geom_type == 0:
        ring = ogr.Geometry(ogr.wkbLinearRing)    
    else:
        ring = ogr.Geometry(ogr.wkbLineString)    
    for i in range (0,p_len):
        ring.AddPoint(points[i,0], points[i,1])
    #output_area = ring.Area()
    if points[0,0]!=points[p_len-1,0] or points[0,1]!=points[p_len-1,1]:
        ring.AddPoint(points[0,0], points[0,1])
    return 1,ring

#-----------------------------------------------------------------------------------------------------------------
# This functions simplifies open lines. First and last points are same in output which preserves topology.
# Local operator in function Simplify is called first for the smallest segment in line which forms zig-zig with
# its neighbouring segments, and after modification, the smallest segment in modified line is next candidate for
# simplification.
# This way line is almost always treated in the same order (exception can be multiple segments with minimal length)
# and this is very useful for generalisation of duplicate lines, because such borders will remain very close, or
# equal on some parts. Other advantage is that it gives kind of global property to generalisation, meaning that
# line can be generalised multiple times through intermediate scales or directly to final smaller scale, and result 
# should be same or very similar.
#------------------------------------------------------------------------------------------------------------------  
    
def Simplify_Line(g):
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] or points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list
    
    #malformed linear geometry
    if p_len <= 1:
        return 0,g
    #segment or two segments, nothing to generalize, return cleaned geometry    
    if p_len <= 3:
        line = ogr.Geometry(ogr.wkbLineString)    
        for i in range (0,p_len):
            line.AddPoint(points[i,0], points[i,1])
        return -1,line
        
    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i], points[i+1])
           
    i = np.argmin(segments) #index of shorthest segment
    min_s = np.amin(segments) #squared length of shorthest segment
    while min_s < SQR_TOL_LENGTH and p_len > 3:            
        if i>0 and i<p_len-2: #we are not on first or last segment
          if zig_zag(points[i-1],points[i],points[i+1],points[i+2]):
            flag,point = Simplify(points[i-1],points[i],points[i+1],points[i+2])
            if flag == 1:
                points[i] = point
                points = np.delete(points,i+1,0)
                segments = np.delete(segments,i)
                p_len = p_len - 1
                #calculate new segments lengths with new point
                segments[i-1] = squared_length(points[i-1], points[i])
                segments[i] = squared_length(points[i], points[i+1])
                #recalculate neigbour segments in case they were set to 2*SQR_TOL_LENGTH
                #check if close to starting/ending point of closed polyline
                #if i == 1:
                #    segments[i+1] = squared_length(points[i+1], points[i+2])
                #elif i == p_len-2:
                #    segments[i-2] = squared_length(points[i-2], points[i-1])
                #else:  
                #    segments[i-2] = squared_length(points[i-2], points[i-1])
                #    segments[i+1] = squared_length(points[i+1], points[i+2])
          else:
            segments[i] = 2*SQR_TOL_LENGTH
        else:
            segments[i] = 2*SQR_TOL_LENGTH
        i = np.argmin(segments) #index of new shortest segment
        min_s = np.amin(segments) #squared length of new shortest segment
    
    line = ogr.Geometry(ogr.wkbLineString)    
    for i in range (0,p_len):
        line.AddPoint(points[i,0], points[i,1])
        
    return 1,line

#------------------------------------------------------------------------------------------------------------------
# Main smoothing function.
# Takes three consecutive points forming two consecutive segments in line.
# Algorithm preserves p1 and p3. Vertex p2 is replaced by now points ps and pq in a way that
# p1-ps-pq-p3-p1 forms an isosceles trapesoid with less sharper angles then input one.
#
# TODO: This is fairly complicated computation for each iteration and performance should be improved
# TODO: ps and pq does not have to form only isosceles trapesoid in order to preserve area. Parallel movement
# along line ps-pq is possible and maximal area of intersection of figures p1-p2-p3-p1 and p1-pq-pq-p3-p1 
# could be obtained. This should improve quality of smoothing.
#------------------------------------------------------------------------------------------------------------------    
    
def Smooth(p1,p2,p3):
    ps = np.zeros(2) #temp point for calculation
    pq = np.zeros(2) #temp point for calculation
    aa = squared_length(p1,p3) #square of length of base p1p3
    a = math.sqrt(aa)  #length of base p1p3
    P = 0.5*abs(p1[1]*(p3[0]-p2[0])+p2[1]*(p1[0]-p3[0])+p3[1]*(p2[0]-p1[0])) #area of triangle p1p2p3
    PP = P*P #square of area of triangle p1p2p3
    A = math.pow(432.*PP*(math.sqrt(aa*aa+16.*PP)-aa),0.33333333333333333333) #Ferrari's method for solution of 4th degree polynom
    B = 0.5*A-72.*PP/A
    z = math.sqrt(aa+B)
    z = -3.*a+z+math.sqrt(2.*aa-B+2.*aa*a/z)
    b = (z+a)/3. #length of the three new segments, they are equal and form isosceles trapesoid

    #calculate the coordinates of the new points ps and pq
    if ((p3[1]-p1[1])==0.): #special case when the base is parallel with x
        q = 0.; p = 2.*P/(a+b)
    else:  
        alpha = -(p3[0]-p1[0])/(p3[1]-p1[1])
        q = 2.*P/(math.sqrt(1.+alpha*alpha)*(a+b))
        p = alpha*q
    ps[1] = (p3[1]-p1[1])*0.5*(1.-b/a)+p1[1]+p
    ps[0] = (p3[0]-p1[0])*0.5*(1.-b/a)+p1[0]+q # coordinates of new points
    pq[1] = (p3[1]-p1[1])*0.5*(1.+b/a)+p1[1]+p
    pq[0] = (p3[0]-p1[0])*0.5*(1.+b/a)+p1[0]+q

    #from two solutions choose one with same orientation as original triangle
    if ((p1[1]*(p3[0]-p2[0])+p2[1]*(p1[0]-p3[0])+p3[1]*(p2[0]-p1[0]))*(p1[1]*(p3[0]-ps[0])+ps[1]*(p1[0]-p3[0])+p3[1]*(ps[0]-p1[0]))<0.):
        ps[1] -= 2.*p
        ps[0] -= 2.*q
        pq[1] -= 2.*p
        pq[0] -= 2.*q
    return ps,pq    
 
#-----------------------------------------------------------------------------------------------------------------
# This functions smoothes closed lines (rings). 
# Closed lines are treated in a way that no point is considered as starting or ending point and each point
# can be deleted or moved. This gives better output, as the line is redrawed manually.
# Local operator in function Smooth is called first for the sharpest angle in line, and after modification, 
# the sharpest angle in modified line is next candidate for smoothing.
# This way line is almost always treated in the same order (exception can be multiple segments with minimal length)
# and this is very useful for generalisation of neighbouring polygons, because borders will remain very close, or
# equal on some parts. Other advantage is that it gives kind of global property to generalisation, meaning that
# line can be generalised multiple times through intermediate scales or directly to final smaller scale, and result 
# should be same or very similar.
#------------------------------------------------------------------------------------------------------------------   
 
def Smooth_Ring(g,geom_type):

    input_area = g.Area()
    if input_area < DEL_AREA:
        return 0,g #area of ring is too small to keep on map   
   
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] or points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list

    #malformed closed linear geometry, for closed one at least 4 points are needed
    if p_len < 4:
        return 0,g
           
    ps = np.zeros(2) #temp point for calculation
    pq = np.zeros(2) #temp point for calculation
    
    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i], points[i+1])
    
    angles = np.zeros(p_len-1)
    #angles[0] is angle on starting=ending point
    angles[0] = segments_angle(points[p_len-2],points[0],points[1])
    for i in range(1, p_len-1):
        #angles[1] is angle on vertex point[1]
        angles[i] = segments_angle(points[i-1], points[i], points[i+1])

    #always change the sharpest angle in line
    i = np.argmin(angles) #index of sharpest angle
    min_a = np.amin(angles) #sharpest angle
    while min_a < MIN_ANGLE:  
        if i == 0:     
            if segments[p_len-2] < SQR_SMOOTH_LENGTH and segments[i] < SQR_SMOOTH_LENGTH:
                #TODO: check what is going on here!
                #calculation of the two new points, keeping the area
                ps,pq = Smooth(points[p_len-2], points[i], points[i+1])      
                #update the point list
                points[i] = ps #change starting point
                points[p_len-1] = ps #change ending point
                points = np.insert(points,i+1,pq,0) #add new point before point after middle point
                p_len = p_len + 1
                segments = np.insert(segments,i+1,squared_length(points[i+1],points[i+2]),0) #add last segment
                segments[p_len-2] = squared_length(points[p_len-2],points[i]) #update middle segment
                segments[i] = squared_length(points[i],points[i+1]) #update first segment
                angles = np.insert(angles,i+1,segments_angle(points[i], points[i+1], points[i+2])) #add angle on point pq
                angles[i] = segments_angle(points[p_len-2], points[i], points[i+1])
                angles[p_len-2] = segments_angle(points[p_len-3], points[p_len-2], points[i])
                angles[i+2] = segments_angle(points[i+1], points[i+2], points[i+3])
                #angles[i] =  2*MIN_ANGLE  #check what happens, meanwhile skip this angle
            else:
                angles[i] =  2*MIN_ANGLE  #angle was sharp but segments were too long, skip it in next iteration     
            #if segments are smaller then threshold
        else:
            if segments[i-1] < SQR_SMOOTH_LENGTH and segments[i] < SQR_SMOOTH_LENGTH:
                #calculation of the two new points, keeping the area
                ps,pq = Smooth(points[i-1], points[i], points[i+1])    
                #update the point list
                points[i] = ps #change middle point
                points = np.insert(points,i+1,pq,0) #add new point before point after middle point
                segments = np.insert(segments,i+1,squared_length(points[i+1],points[i+2]),0) #add last segment
                segments[i-1] = squared_length(points[i-1],points[i]) #update middle segment
                segments[i] = squared_length(points[i],points[i+1]) #update first segment
                angles = np.insert(angles,i+1,segments_angle(points[i], points[i+1], points[i+2])) #add angle on point pq
                angles[i] = segments_angle(points[i-1], points[i], points[i+1])
                if i==1:
                    angles[i-1] = segments_angle(points[p_len-2], points[p_len-1], points[i])
                else:
                    angles[i-1] = segments_angle(points[i-2], points[i-1], points[i])
                if i == p_len-2:    
                    angles[0] = segments_angle(points[p_len-2], points[0], points[1])
                else:    
                    angles[i+2] = segments_angle(points[i+1], points[i+2], points[i+3])
                p_len = p_len + 1
            else:
                angles[i] =  2*MIN_ANGLE  #angle was sharp but segments were too long, skip it in next iteration     
            #if segments are smaller then threshold
        # if smallest angle is on starting point        
        i = np.argmin(angles) #index of sharpest angle
        min_a = np.amin(angles) #sharpest angle
    #while angle is smaller then threshold
        
    if geom_type == 0:
        ring = ogr.Geometry(ogr.wkbLinearRing)    
    else:
        ring = ogr.Geometry(ogr.wkbLineString)    
    for i in range (0,p_len):
        ring.AddPoint(points[i,0], points[i,1])
    if points[0,0]!=points[p_len-1,0] or points[0,1]!=points[p_len-1,1]:
        ring.AddPoint(points[0,0], points[0,1])
    return 1,ring

#-----------------------------------------------------------------------------------------------------------------
# This functions smoothes open lines. First and end points are preserved in output.
# Local operator in function Smooth is called first for the sharpest angle in line, and after modification, 
# the sharpest angle in modified line is next candidate for smoothing.
# This way line is almost always treated in the same order (exception can be multiple segments with minimal length)
# and this is very useful for generalisation of neighbouring polygons, because borders will remain very close, or
# equal on some parts. Other advantage is that it gives kind of global property to generalisation, meaning that
# line can be generalised multiple times through intermediate scales or directly to final smaller scale, and result 
# should be same or very similar.
#------------------------------------------------------------------------------------------------------------------   
    
def Smooth_Line(g):
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] or points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list
    
    #malformed linear geometry, zero or one point
    if p_len < 2:
        return 0,g
    #geometry of one segment, nothing to smooth, return cleaned    
    if p_len == 2:    
        line = ogr.Geometry(ogr.wkbLineString)    
        for i in range (0,p_len):
            line.AddPoint(points[i,0], points[i,1])
        return -1,line
        
    ps = np.zeros(2) #temp point for calculation
    pq = np.zeros(2) #temp point for calculation
    
    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i], points[i+1])
    
    angles = np.zeros(p_len-1)
    #angles[0] is angle on first point
    angles[0] = 2*MIN_ANGLE
    for i in range(1, p_len-1):
        #angles[0] is angle on vertex point[1]
        angles[i] = segments_angle(points[i-1], points[i], points[i+1])

    #always change the sharpest angle in line
    i = np.argmin(angles) #index of sharpest angle
    min_a = np.amin(angles) #sharpest angle
    while min_a < MIN_ANGLE:  
        if segments[i-1] < SQR_SMOOTH_LENGTH and segments[i] < SQR_SMOOTH_LENGTH:
            #calculation of the two new points, keeping the area
            ps,pq = Smooth(points[i-1], points[i], points[i+1])    
            #update the point list
            points[i] = ps #change middle point
            points = np.insert(points,i+1,pq,0) #add new point before point after middle point
            segments = np.insert(segments,i+1,squared_length(points[i+1],points[i+2]),0) #add last segment
            segments[i-1] = squared_length(points[i-1],points[i]) #update middle segment
            segments[i] = squared_length(points[i],points[i+1]) #update first segment
            angles = np.insert(angles,i+1,segments_angle(points[i], points[i+1], points[i+2])) #add angle on point pq
            angles[i] = segments_angle(points[i-1], points[i], points[i+1])
            if i>1:
                angles[i-1] = segments_angle(points[i-2], points[i-1], points[i])
            if i < p_len-2:    
                angles[i+2] = segments_angle(points[i+1], points[i+2], points[i+3])
            p_len = p_len + 1
        else:
            angles[i] =  2*MIN_ANGLE  #angle was sharp but segments were too long, skip it in next iteration     
        #if segments are smaller then threshold
        i = np.argmin(angles) #index of sharpest angle
        min_a = np.amin(angles) #sharpest angle
    #while angle is smaller then threshold

    line = ogr.Geometry(ogr.wkbLineString)    
    for i in range (0,p_len):
        line.AddPoint(points[i,0], points[i,1])
    
    return 1,line
    

#-----------------------------------------------------------------------------------------------------------
# Decide how the geometry will be treated, e.g. rings, lines, single geometries or multiple geometries
# TODO: Shorten code, e.g. alg_type == 0 is combination of alg_type == 1 and alg_type == 2
#-----------------------------------------------------------------------------------------------------------
    
def Decide(g,closed,g_type,out_geom,alg_type,single_line):
    gen = 0 #assume there is nothing to preserve after generalisation
    
    if alg_type == 0: #perform simplification and smoothing
        if closed: #rings are allways closed, for lines it is determined in advance
            flag,simpl = Simplify_Ring(g,g_type) #g_type == 0 means ring and g_type=1 means closed line
        else:
            flag,simpl = Simplify_Line(g) #flag == 0 means that geometry should be deleted from output     
        if flag == 1 or flag == -1: #flag == 1 means some simplification happened, proceed with smoothing 
            if closed:
                flag,smooth = Smooth_Ring(simpl,g_type) #g_type == 0 means ring and g_type=1 means closed line
            else:
                flag,smooth = Smooth_Line(simpl) #flag == 0 means that geometry should be deleted from output     
            if flag == 1 or flag == -1: #flag == -1 means that geometry was not changed by smoothing but it should be preserved in output
                if single_line: #single geometry, direct assignment
                    out_geom = smooth
                else: #multigeometry, add part to it   
                    out_geom.AddGeometry(smooth)
                gen = 1 #there is geometry to preserve in output
            
    if alg_type == 1: #perform only simplification, same as alg_type==0, but only simplification is performed
        if closed:
            flag,simpl = Simplify_Ring(g,g_type) 
        else:
            flag,simpl = Simplify_Line(g)                    
        if flag == 1 or flag == -1:
            if single_line:
                out_geom = simpl
            else:    
                out_geom.AddGeometry(simpl)
            gen = 1
            
    if alg_type == 2: #perform only smoothing, , same as alg_type==0, but only simplification is performed
        if closed:
            flag,smooth = Smooth_Ring(g,g_type)
        else:
            flag,smooth = Smooth_Line(g)                       
        if flag == 1 or flag == -1:
            if single_line:
                out_geom = smooth
            else:    
                out_geom.AddGeometry(smooth)
            gen = 1
    if alg_type == 3: #perform simplification of orthogonal segments
        flag,simpl = Simplify_Line_Ortho(g,closed,g_type) 
        if flag == 1 or flag == -1:
            if single_line:
                out_geom = simpl
            else:    
                out_geom.AddGeometry(simpl)
            gen = 1
           
    return gen,out_geom


    
#-------------------------------------------------------------------------------------------------------------
# Main function called for a generalisation of geometry in ESRI Shapefile
# TODO: Allow different file formats
#
# Arguments: 
#    scale - map scale denominator for which generalisation as on paper topographic maps will be performed
#            for more generalisation increase scale denominator, and for less generalisation decrease its value
#    small_area - 0.5 mmm2 in map scale, minimal size readible on maps
#            could be left to user to define
#    alg_type - 0 = full generalisation (simplification and smoothing)
#               1 = only simplification
#               2 = only smoothing
#               3 = orthogonal segments
#    inFile - filename of input ESRI Shapefile
#    outFile - filename of output ESRI Shapefile
#--------------------------------------------------------------------------------------------------------------

def progress_changed(progress):
    progressbar.setValue(progress)     
    
def Generalize(scale,small_area,alg_type,inFile,outFile):   

    
    global DEL_AREA
    global TOL_LENGTH
    global SQR_TOL_LENGTH
    global ZERO_EPSILON
    global MIN_ANGLE
    global SQR_SMOOTH_LENGTH
    global ZERO_AREA

    DEL_AREA = (scale/1000)*(scale/1000)*small_area #small area in map units
    TOL_LENGTH = scale/5000 #main paramater of the algorithm, determined from manually generalised maps
    SQR_TOL_LENGTH = TOL_LENGTH*TOL_LENGTH #squared main parameter of the algorithm
    ZERO_EPSILON = 1E-12 # if less then value is considered as zero
    MIN_ANGLE = 150.*math.pi/180. # min segments angle in smoothed line, increase to get even smoother lines with more vertices
    SQR_SMOOTH_LENGTH = 20.*SQR_TOL_LENGTH # max segments length for smoothing, longer segments can form sharper angles then MIN_ANGLE
    ZERO_AREA = 1E-6 # if less then value is considered as zero
    
    #open input ESRI Shapefile
    driver = ogr.GetDriverByName('ESRI Shapefile')
    inDataSet = driver.Open(inFile, 0)
    inLayer = inDataSet.GetLayer()
    
    #create output ESRI Shapefile
    if os.path.exists(outFile):
        driver.DeleteDataSource(outFile)
    outDataSet = driver.CreateDataSource(outFile)
    outLayer = outDataSet.CreateLayer(inLayer.GetName(), geom_type=inLayer.GetGeomType())

    #copy fields to output 
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    #get the output layer's feature definition, will be used for copying field values to output
    outLayerDefn = outLayer.GetLayerDefn()
    num_of_objects = inLayer.GetFeatureCount()
    obj_index = 0
    #loop through all input features and generalize them 
    for inFeature in inLayer:
        #update progress bar 
        obj_index = obj_index + 1
        progress_changed(obj_index/num_of_objects*100)

        gen = 0 #assume the feature should be omitted from output
        geom = inFeature.geometry() #get reference of feature geometry
        if geom.GetGeometryName() == 'MULTIPOLYGON':
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon) #create output geometry of given type
            for i in range(0, geom.GetGeometryCount()): #iterate over polygons in multipolygon
                poly = ogr.Geometry(ogr.wkbPolygon) #create output polygon geometry
                g = geom.GetGeometryRef(i) # input polygon can have multiple rings
                for j in range(0, g.GetGeometryCount()): #iterate over rings
                    ring = g.GetGeometryRef(j) #access to a ring (closed polyline)
                    
                    #output: gen_ring=1 indicates that some geometry is preserved after generalisation
                    #output: poly will receive all generalised rings in it
                    #input: True means that rings are allways closed
                    #input: first 0 means that ogrLinearRing is geometry type for creation
                    #input: poly is reference to geometry in which new generalised geometry of right type will be stored
                    #input: alg_type - generalisation (simplification+smoothing), simplification or smoothing
                    #input: second 0 means that this is multigeometry (polygon with multiple rings)
                    gen_ring,poly = Decide(ring,True,0,poly,alg_type,0) #perform generalisation
                    
                    #there were some geometry preserved, store this in gen so output feature will be created
                    #some parts could be deleted due to too small area for given scale
                    if gen_ring == 1:
                        gen = 1
                #add polygon to multipolygon                       
                out_geom.AddGeometry(poly)  
                
        elif geom.GetGeometryName() == 'POLYGON':
            out_geom = ogr.Geometry(ogr.wkbPolygon) #create output geometry of given type
            for i in range(0, geom.GetGeometryCount()): #iterate over rings
                ring = geom.GetGeometryRef(i) #access to a ring (closed polyline)
                
                #output: gen_ring=1 indicates that some geometry is preserved after generalisation
                #output: out_geom will receive all generalised rings in it
                #input: True means that rings are allways closed
                #input: first 0 means that ogrLinearRing is geometry type for creation
                #input: out_geom is reference to geometry in which new generalised geometry of right type will be stored
                #input: alg_type - generalisation (simplification+smoothing), simplification or smoothing
                #input: second 0 means that this is multigeometry (polygon with multiple rings)
                gen_ring,out_geom = Decide(ring,True,0,out_geom,alg_type,0) #perform generalisation

                #there were some geometry preserved, store this in gen so output feature will be created
                #some parts could be deleted due to too small area for given scale
                if gen_ring == 1:
                    gen = 1
                    
        elif geom.GetGeometryName() == 'MULTILINESTRING':
            out_geom = ogr.Geometry(ogr.wkbMultiLineString) #create output geometry of given type
            for i in range(0, geom.GetGeometryCount()): #iterate over lines
                line = geom.GetGeometryRef(i)
                #check if it closed polyline, if so, generalize it as ring, which means 
                #that neither vertex is considered as fixed
                #if line is open, starting and ending points are preserved
                ps = line.GetPoint(0)
                pe = line.GetPoint(line.GetPointCount()-1)
                closed = False
                if (ps[0] == pe[0]) and (ps[1] == pe[1]):
                    closed = True
                    
                #output: gen_line=1 indicates that some geometry is preserved after generalisation
                #output: out_geom will receive all generalised lines in it
                #input: closed indicates whether line is closed or not
                #input: 1 means that ogrLineString is geometry type for creation
                #input: out_geom is reference to geometry in which new generalised geometry of right type will be stored
                #input: alg_type - generalisation (simplification+smoothing), simplification or smoothing
                #input: 0 means that this is multigeometry (multilinestring with multiple linestrings)
                gen_line,out_geom = Decide(line,closed,1,out_geom,alg_type,0)    

                #there were some geometry preserved, store this in gen so output feature will be created  
                #some parts could be deleted due to too small area for given scale                
                if gen_line == 1:
                    gen = 1
                    
        elif geom.GetGeometryName() == 'LINESTRING':
            out_geom = ogr.Geometry(ogr.wkbLineString) #create output geometry of given type
            # check if it closed polyline, if so, generalize it as ring, which means 
            #that neither vertex is considered as fixed
            #if line is open, starting and ending points are preserved
            ps = geom.GetPoint(0)
            pe = geom.GetPoint(geom.GetPointCount()-1)
            closed = False
            if (ps[0] == pe[0]) and (ps[1] == pe[1]):
                closed = True
            #output: gen=1 indicates that geometry is preserved after generalisation
            #output: out_geom will receive generalised line in it
            #input: closed indicates whether line is closed or not
            #input: 1 means that ogrLineString is geometry type for creation
            #input: out_geom is reference to geometry in which new generalised geometry of right type will be stored
            #input: alg_type - generalisation (simplification+smoothing), simplification or smoothing
            #input: 1 means that this is single geometry (one linestring)
            gen,out_geom = Decide(geom,closed,1,out_geom,alg_type,1) 
        
        #if some geometry is preserved after generalisation create output feature with 
        #generalised geometry and copy attributes from input feature        
        if gen == 1: 
            outFeature = ogr.Feature(outLayerDefn)
            #set the geometry 
            outFeature.SetGeometry(out_geom)
            #copy the attributes
            for i in range(0, outLayerDefn.GetFieldCount()):
                outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
            #add the feature to the shapefile
            outLayer.CreateFeature(outFeature)
            #destroy output feature
            outFeature.Destroy()
        #destroy input feature and get the next input feature    
        inFeature.Destroy()
        
    #create .prj file for output if CRS is attached to input layer
    spatialRef = inLayer.GetSpatialRef()
    if spatialRef is not None:
        spatialRef.MorphToESRI()
        file = open(os.path.splitext(outFile)[0]+'.prj', 'w')
        file.write(spatialRef.ExportToWkt())
        file.close()
        
    #destroy datasets which will also close files
    inDataSet.Destroy()
    outDataSet.Destroy()
