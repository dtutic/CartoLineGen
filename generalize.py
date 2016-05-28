import ogr,sys,math,random,os
import numpy as np

def zig_zag(a,b,c,d): #returns true if three segments form zig-zag
    return (a[1]*(c[0]-b[0])+b[1]*(a[0]-c[0])+c[1]*(b[0]-a[0]))*(b[1]*(d[0]-c[0])+c[1]*(b[0]-d[0])+d[1]*(c[0]-b[0])) < ZERO_EPSILON

def polygon_area(a,b,c,d): #surveyors formula for 4 points
    return (b[0]-a[0])*(b[1]+a[1])+(c[0]-b[0])*(c[1]+b[1])+(d[0]-c[0])*(d[1]+c[1]) 

def polygon_area_closed(a,b,c,d): #surveyors formula for 4 points
    return a[0]*(b[1]-d[1])+b[0]*(c[1]-a[1])+c[0]*(d[1]-b[1])+d[0]*(a[1]-c[1])

def squared_length(p1,p2):
    return (p1[0]-p2[0])*(p1[0]-p2[0])+(p1[1]-p2[1])*(p1[1]-p2[1])    

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
 
def Generalize_Ring(g):
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
        if points[j,0] != p[0] and points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list

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
        
    ring = ogr.Geometry(ogr.wkbLinearRing)    
    for i in range (0,p_len):
        ring.AddPoint(points[i,0], points[i,1])
    output_area = ring.Area()
    if points[0,0]!=points[p_len-1,0] or points[0,1]!=points[p_len-1,1]:
        ring.AddPoint(points[0,0], points[0,1])
    return 1,ring

def Generalize_Line(g):
  
    p_len = g.GetPointCount()
    points = np.zeros((p_len,2))
    j = 0
    p = g.GetPoint(j)
    points[j,0] = p[0]
    points[j,1] = p[1]
    for i in range(1, p_len):
        p = g.GetPoint(i)
        #remove duplicate neighbour points
        if points[j,0] != p[0] and points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list

    #calculate squared segments lengths, algorithm always change line where shorthest segment is found
    segments = np.zeros(p_len-1)
    for i in range(0, p_len-1):
        segments[i] = squared_length(points[i], points[i+1])
           
    i = np.argmin(segments) #index of shorthest segment
    min_s = np.amin(segments) #squared length of shorthest segment
    while min_s < SQR_TOL_LENGTH and p_len > 4:            
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
                if i == 1:
                    segments[i+1] = squared_length(points[i+1], points[i+2])
                elif i == p_len-2:
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                else:  
                    segments[i-2] = squared_length(points[i-2], points[i-1])
                    segments[i+1] = squared_length(points[i+1], points[i+2])
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
    
def Smooth_Ring(g):

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
        if points[j,0] != p[0] and points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list

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
                #ps,pq = Smooth(points[p_len-2], points[i], points[i+1])      
                #update the point list
                #points[i] = ps #change starting point
                #points[p_len-1] = ps #change ending point
                #points = np.insert(points,i+1,pq,0) #add new point before point after middle point
                #segments = np.insert(segments,i+1,squared_length(points[i+1],points[i+2]),0) #add last segment
                #segments[p_len-2] = squared_length(points[p_len-2],points[i]) #update middle segment
                #segments[i] = squared_length(points[i],points[i+1]) #update first segment
                #angles = np.insert(angles,i+1,segments_angle(points[i], points[i+1], points[i+2])) #add angle on point pq
                #angles[i] = segments_angle(points[p_len-2], points[i], points[i+1])
                #angles[p_len-2] = segments_angle(points[p_len-3], points[p_len-2], points[i])
                #angles[i+2] = segments_angle(points[i+1], points[i+2], points[i+3])
                #p_len = p_len + 1
                angles[i] =  2*MIN_ANGLE  #check what happens, meanwhile skip this angle
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

    ring = ogr.Geometry(ogr.wkbLinearRing)    
    for i in range (0,p_len):
        ring.AddPoint(points[i,0], points[i,1])
    if points[0,0]!=points[p_len-1,0] or points[0,1]!=points[p_len-1,1]:
        ring.AddPoint(points[0,0], points[0,1])
    return 1,ring

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
        if points[j,0] != p[0] and points[j,1] != p[1]:
            j = j+1
            points[j,0] = p[0]
            points[j,1] = p[1]
    p_len = j+1 #final number of points in point list

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
    
#start of main program
def Generalize(scale,small_area,inFile,outFile):    
    global DEL_AREA
    global TOL_LENGTH
    global SQR_TOL_LENGTH
    global ZERO_EPSILON
    global MIN_ANGLE
    global SQR_SMOOTH_LENGTH
    
    DEL_AREA = (scale/1000)*(scale/1000)*small_area #small area in map units
    TOL_LENGTH = scale/2300 #main paramater of the algorithm
    SQR_TOL_LENGTH = TOL_LENGTH*TOL_LENGTH #squared main parameter of the algorithm
    ZERO_EPSILON = 1E-12 # treat as zero
    MIN_ANGLE = 150.*math.pi/180.
    SQR_SMOOTH_LENGTH = 20.*SQR_TOL_LENGTH
    
    driver = ogr.GetDriverByName('ESRI Shapefile')
    inDataSet = driver.Open(inFile, 0)
    
    inLayer = inDataSet.GetLayer()
    
    if os.path.exists(outFile):
        driver.DeleteDataSource(outFile)
    outDataSet = driver.CreateDataSource(outFile)
    outLayer = outDataSet.CreateLayer(inLayer.GetName(), geom_type=inLayer.GetGeomType())

    # add fields
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    # get the output layer's feature definition
    outLayerDefn = outLayer.GetLayerDefn()

    for inFeature in inLayer:
        geom = inFeature.GetGeometryRef()
        if geom.GetGeometryName() == 'MULTIPOLYGON':
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for i in range(0, geom.GetGeometryCount()): #iterate over polygons
                poly = ogr.Geometry(ogr.wkbPolygon) 
                g = geom.GetGeometryRef(i) #polygon can have multiple rings
                for j in range(0, g.GetGeometryCount()): #iterate over rings
                    ring = g.GetGeometryRef(j) #access to a ring (closed polyline)
                    flag,simpl = Generalize_Ring(ring) 
                    if flag == 1:
                        flag,smooth = Smooth_Ring(simpl)
                        poly.AddGeometry(smooth)
                out_geom.AddGeometry(poly)                      
        elif geom.GetGeometryName() == 'POLYGON':
            out_geom = ogr.Geometry(ogr.wkbPolygon) 
            for i in range(0, geom.GetGeometryCount()): #iterate over rings
                g = geom.GetGeometryRef(i) #access to a ring (closed polyline)
                flag,simpl = Generalize_Ring(g)
                if flag == 1:
                    flag,smooth = Smooth_Ring(simpl)
                    out_geom.AddGeometry(smooth)
        elif geom.GetGeometryName() == 'MULTILINESTRING':
            out_geom = ogr.Geometry(ogr.wkbMultiLineString)
            for i in range(0, geom.GetGeometryCount()): #iterate over lines
                g = geom.GetGeometryRef(i) 
                flag,simpl = Generalize_Line(g) 
                if flag == 1:
                    flag,smooth = Smooth_Line(simpl)
                    out_geom.AddGeometry(smooth)
        elif geom.GetGeometryName() == 'LINESTRING':
            line = ogr.Geometry(ogr.wkbLineString) 
            flag,simpl = Generalize_Line(geom)
            flag,out_geom = Smooth_Line(simpl)
        outFeature = ogr.Feature(outLayerDefn)
        # set the geometry and attribute
        outFeature.SetGeometry(out_geom)
        for i in range(0, outLayerDefn.GetFieldCount()):
            outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
        # add the feature to the shapefile
        outLayer.CreateFeature(outFeature)
        # destroy the features and get the next input feature
        outFeature.Destroy()
        inFeature.Destroy()
        
    #create .prj file
    spatialRef = inLayer.GetSpatialRef()
    spatialRef.MorphToESRI()
    file = open(os.path.splitext(outFile)[0]+'.prj', 'w')
    file.write(spatialRef.ExportToWkt())
    file.close()

    inDataSet.Destroy()
    outDataSet.Destroy()
