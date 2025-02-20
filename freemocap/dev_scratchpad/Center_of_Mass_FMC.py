import cv2
import mediapipe as mp
import numpy as np
import math
mp_drawing = mp.solutions.drawing_utils #gives us all our drawing capabilities
mp_pose = mp.solutions.pose #importing our pose estimatino models

### center of mass functions
def count_frames(cap):
    nframe = 0
    while True:
        (grabbed, frame) = cap.read()
        if not grabbed:
            break
        nframe += 1
    return nframe

def calculateCOM_x(x1, x2, com_proximal_multiplier):
    segment_length_x = x2-x1
    COM_x = x1+com_proximal_multiplier*segment_length_x
    return COM_x

def calculateCOM_y(y1, y2, com_proximal_multiplier):
    segment_length_y = y2 - y1
    COM_y = y1+com_proximal_multiplier*segment_length_y
    return COM_y

def calculate_foot_COM_x(heel_x, ankle_x, foot_index_x):
    COM_foot_x = (heel_x + ankle_x + foot_index_x)/3
    return COM_foot_x

def calculate_foot_COM_y(heel_y, ankle_y, foot_index_y):
    COM_foot_y = (heel_y + ankle_y + foot_index_y)/3
    return COM_foot_y

def calculate_hand_COM_x(wrist_x, index_x, pinky_x, com_proximal_multiplier):
    knuckle_width_x = pinky_x - index_x
    Third_metacarple_x = index_x + knuckle_width_x/3
    Palm_segment_x = Third_metacarple_x - wrist_x
    COM_hand_x = wrist_x + com_proximal_multiplier*Palm_segment_x
    return COM_hand_x

def calculate_hand_COM_y(wrist_y, index_y, pinky_y, com_proximal_multiplier):
    knuckle_width_y = pinky_y - index_y
    Third_metacarple_y = index_y + knuckle_width_y/3
    Palm_segment_y = Third_metacarple_y - wrist_y
    COM_hand_y = wrist_y + com_proximal_multiplier*Palm_segment_y
    return COM_hand_y

def calculate_total_COM_x(COM_Segments):
    Segment_COM_List_x = []

    for key in COM_Segments:
        COM_of_Segment = COM_Segments[key][2]*COM_Segments[key][0]
        Segment_COM_List_x.append(COM_of_Segment)
    COM_total_x = sum(Segment_COM_List_x)
    return COM_total_x,Segment_COM_List_x

def calculate_total_COM_y(COM_Segments):
    Segment_COM_List_y = []

    for key in COM_Segments:
        COM_of_Segment = COM_Segments[key][2]*COM_Segments[key][1]
        Segment_COM_List_y.append(COM_of_Segment)
    COM_total_y = sum(Segment_COM_List_y)
    return COM_total_y, Segment_COM_List_y
#### 

## Multipliers are percent of segment length from the proximal end point. 
head_multiplier_f = 0.5894
head_multiplier_m = 0.5976
trunk_multiplier_f = 0.3782
trunk_multiplier_m = 0.4310
upper_arm_multiplier_f = 0.5754
upper_arm_multiplier_m = 0.5772
forearm_multiplier_f = 0.4559
forearm_multiplier_m = 0.4574
hand_multiplier_f = 0.7474
hand_multiplier_m = 0.7900
thigh_multiplier_f = 0.3612
thigh_multiplier_m = 0.4095
shin_multiplier_f = 0.4416
shin_multiplier_m = 0.4459
foot_multiplier_f = 0.4014
foot_multiplier_m = 0.4415

## mass percent of each body segment compared to full body mass. 
head_mass_percent_f = 0.0668
head_mass_percent_m = 0.0694
trunk_mass_percent_f = 0.4257
trunk_mass_percent_m = 0.4346
upper_arm_mass_percent_f = 0.0255
upper_arm_mass_percent_m = 0.0271
forearm_mass_percent_f = 0.0138
forearm_mass_percent_m = 0.0162
hand_mass_percent_f = 0.0056
hand_mass_percent_m = 0.0061
thigh_mass_percent_f = 0.1478
thigh_mass_percent_m = 0.1416
shin_mass_percent_f = 0.0481
shin_mass_percent_m = 0.0433
foot_mass_percent_f = 0.0129
foot_mass_percent_m = 0.0137


cap = cv2.VideoCapture("C:/Users/kiley/Desktop/Mediapipe_Output_Videos/Processed_Video_2.avi")

if cap.isOpened():
    vid_res_width = cap.get(3)
    vid_res_height = cap.get(4)
    
print('width', vid_res_width)
print('height', vid_res_height)

# Building array to fit COM points into FMC 3D reconstruction code
ncams_list = [1] #replace this eventually with a way to count how many cameras there are. For now, we only have 1
nframe = count_frames(cap) #extract the number of frames in each video
print(nframe)
nframes_list = list(range(1, nframe+1))#create a list from 0 to nframes+1, incrementing by 1. nframes+1 because range function doesn't include the final number. 
print(nframes_list)
nImages = 15 #there are 15 COM points to plot
nImages_list = list(range(0, nImages+1)) 
print(nImages_list)
FMC_COM_array_ncams_nFrames_nImgPts_X_Y = np.empty((nframe*nImages*ncams_list[-1], 5), float) 
print(np.shape(FMC_COM_array_ncams_nFrames_nImgPts_X_Y))
#there are 15 COM points to plot, and 5 columns (for now, will add Confidence column later, need to cacluclate it first)

with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
    while cap.isOpened(): #loop through feed
        ret, frame = cap.read() #getting an image from feed, 'frame' is our video feed variable
        
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #recolor image into the RGB format (for mediapipe)
        image.flags.writeable = False
        
        results = pose.process(image) #Make detection, storing detection inside the variable 'results'
        
        image.flags.writeable=True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) #Recolor back to BGR (for opencv)
        
        try: #allows for the random dropped frames in webcam video feeds
            landmarks = results.pose_landmarks.landmark
            
            # COM of Hands, creating third metacarple point by taking 1/3 of the disatance of the segment between index and pinky landmarks
            # then adding that distance to the index. Palm segment will be from wrist joint to 3rd metacarple joint.
            # dictionary values arranged in [wrist, index, pinky, com_proximal_multiplier, com_x, com_y] in that order. 
            fmc_COM_array = np.empty()
            Hands = {
                'L_hand' : [landmarks[15], landmarks[19], landmarks[17], hand_multiplier_f, 0, 0],
                'R_hand' : [landmarks[16],landmarks[20], landmarks[18], hand_multiplier_f, 0, 0],
                
            }
            #Hands_2 = {}
            for key in Hands:
                #Knuckle_width is defined as the segment from the distal ends of the second to fifth metacarples (index to pinky landmarks)
                wrist_x = Hands[key][0].x
                wrist_y = Hands[key][0].y
                index_x = Hands[key][1].x
                index_y = Hands[key][1].y
                pinky_x = Hands[key][2].x
                pinky_y = Hands[key][2].y
                com_proximal_multiplier = Hands[key][3] 

                COM_hand_x = calculate_hand_COM_x(wrist_x, index_x, pinky_x, com_proximal_multiplier)
                COM_hand_y = calculate_hand_COM_y(wrist_y, index_y, pinky_y, com_proximal_multiplier)

                cv2.circle(image, center=tuple(np.multiply((COM_hand_x, COM_hand_y), [vid_res_width, vid_res_height]).astype(int)), radius=1, color=(255,0,0), thickness=2)
                Hands[key][4] = COM_hand_x
                Hands[key][5] = COM_hand_y

            #COM of FEET, using the centroid of the triangle formed from heel-ankle-"foot-index" landmarks, arranged in that order in the dictionary values.
            Feet = {
                'L_foot' : [landmarks[29], landmarks[27], landmarks[31], 0, 0],
                'R_foot' : [landmarks[30], landmarks[28], landmarks[32], 0, 0]
            }

            for key in Feet:
                heel_x = Feet[key][0].x
                ankle_x = Feet[key][1].x
                foot_index_x = Feet[key][2].x

                heel_y = Feet[key][0].y
                ankle_y = Feet[key][1].y
                foot_index_y = Feet[key][2].y

                COM_foot_x = calculate_foot_COM_x(heel_x, ankle_x, foot_index_x)
                COM_foot_y = calculate_foot_COM_y(heel_y, ankle_y, foot_index_y)

                cv2.circle(image, center=tuple(np.multiply((COM_foot_x, COM_foot_y), [vid_res_width, vid_res_height]).astype(int)), radius=1, color=(255,0,0), thickness=2)

                Feet[key][3] = COM_foot_x
                Feet[key][4] = COM_foot_y

            
            #Trunk segment calculations from MidShoulder to Mid Hip. 
            MidShoulder_x = (landmarks[12].x + landmarks[11].x)/2
            MidShoulder_y = (landmarks[12].y + landmarks[11].y)/2
            MidHip_x = (landmarks[24].x + landmarks[23].x)/2
            MidHip_y = (landmarks[24].y + landmarks[23].y)/2
            TrunkCOM_x = calculateCOM_x(MidShoulder_x, MidHip_x, 0.3782)
            TrunkCOM_y = calculateCOM_y(MidShoulder_y, MidHip_y, 0.3782)

            cv2.circle(image, center=tuple(np.multiply((TrunkCOM_x, TrunkCOM_y), [vid_res_width, vid_res_height]).astype(int)), radius=1, color=(255,0,0), thickness=2)
            # cv2.circle(image, center=tuple((TrunkCOM_x*vid_res_width, TrunkCOM_y*vid_res_height)), radius=4, color=(255,0,0), thickness=2)

            #Body Segment Dictionary format: key = body segment, % value = [proximal joint landmark values, distal joint landmark values, COM as a % of segment length]
            Body_Segments = {
                'L_UpperArm' : [landmarks[11] , landmarks[13] , upper_arm_multiplier_f, 0, 0],
                'R_UpperArm' : [landmarks[12] , landmarks[14] , upper_arm_multiplier_f, 0, 0], 
                'L_Forearm' : [landmarks[13] , landmarks[15] , forearm_multiplier_f, 0, 0],
                'R_Forearm' : [landmarks[14] , landmarks[16] , forearm_multiplier_f, 0, 0], 
                'L_Thigh' : [landmarks[23], landmarks[25], thigh_multiplier_f, 0, 0], 
                'R_Thigh' : [landmarks[24], landmarks[26], thigh_multiplier_f, 0, 0],
                'L_Shin' : [landmarks[25], landmarks[27], shin_multiplier_f, 0, 0],
                'R_Shin' : [landmarks[26], landmarks[28], shin_multiplier_f, 0, 0],
                'Head' : [landmarks[7], landmarks[8], 0.5, 0, 0]
            }


            for key in Body_Segments:
                x1 = Body_Segments[key][0].x #proximal joint x value
                y1 = Body_Segments[key][0].y
                x2 = Body_Segments[key][1].x
                y2 = Body_Segments[key][1].y
                com_proximal_multiplier = Body_Segments[key][2]

                COM_x = calculateCOM_x(x1, x2, com_proximal_multiplier)
                COM_y = calculateCOM_y(y1, y2, com_proximal_multiplier)
            
                #Render COM_x and COM_y of the 8 limb segments onto the video feed. 
                cv2.circle(image, center=tuple(np.multiply((COM_x, COM_y), [vid_res_width, vid_res_height]).astype(int)), radius=1, color=(255,0,0), thickness=3)

                Body_Segments[key][3] = COM_x
                Body_Segments[key][4] = COM_y

            COM_Segments = {
                'Head' : [ Body_Segments['Head'][3], Body_Segments['Head'][4], head_mass_percent_f],
                'Trunk' : [ TrunkCOM_x, TrunkCOM_y, trunk_mass_percent_f ],
                'Left_Upper_Arm' : [ Body_Segments['L_UpperArm'][3], Body_Segments['L_UpperArm'][4], upper_arm_mass_percent_f],
                'Right_Upper_Arm' : [ Body_Segments['R_UpperArm'][3], Body_Segments['R_UpperArm'][4], upper_arm_mass_percent_f],
                'Left_Forearm' : [ Body_Segments['L_Forearm'][3], Body_Segments['L_Forearm'][4], forearm_mass_percent_f],
                'Right_Forearm' : [ Body_Segments['R_Forearm'][3], Body_Segments['R_Forearm'][4], forearm_mass_percent_f],
                'Left_Hand' : [Hands['L_hand'][4], Hands['L_hand'][5], hand_mass_percent_f],
                'Right_Hand' : [Hands['R_hand'][4], Hands['R_hand'][5], hand_mass_percent_f],
                'Left_Thigh' : [Body_Segments['L_Thigh'][3], Body_Segments['L_Thigh'][4], thigh_mass_percent_f],
                'Right_Thigh' : [Body_Segments['R_Thigh'][3], Body_Segments['R_Thigh'][4], thigh_mass_percent_f],
                'Left_Shin' : [Body_Segments['L_Shin'][3], Body_Segments['L_Shin'][4], shin_mass_percent_f],
                'Right_Shin' : [Body_Segments['R_Shin'][3], Body_Segments['R_Shin'][4], shin_mass_percent_f],
                'Left_Foot' : [Feet['L_foot'][3], Feet['L_foot'][4], foot_mass_percent_f], 
                'Right_Foot' : [Feet['R_foot'][3], Feet['R_foot'][4], foot_mass_percent_f], 
            }

            COM_total_x = calculate_total_COM_x(COM_Segments)
            COM_total_y = calculate_total_COM_y(COM_Segments)
                

            cv2.circle(image, center=tuple(np.multiply((COM_total_x, COM_total_y), [vid_res_width, vid_res_height]).astype(int)), radius=1, color=(0,255,0), thickness=5)
            
            #Create FMC Array (Currently in development)
            # zip together Segment_COM_List_x and Segment_COM_List_y to create Full_COM_Point_List
            for x in ncams_list:
                for y in nframes_list:
                    for z in nImages_list:
                        index = 0
                        # FMC_COM_array_ncams_nFrames_nImgPts_X_Y[index]=[x, y, z, Full_COM_Point_List[z][0], Full_COM_Point_List[z][1]]
                        index = index + 1
            

        except:
            pass
        
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                  mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                                  mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
                                  )
        #This uses mediapipes drawing utilities to draw the landmarks and the connections onto the image variable. 
        #results.pose_landmarks gives us the mediapipe landmark coordinates XYZC
        #mp_pose.POSE_CONNECTIONS gives us the line connections between points
        # the first line of drawingspec info is the info for the landmarks
        # the second line of drawingspec info is the info for the connection lines
        
        
        cv2.imshow('MediapipeCOM', image)
        
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break
        
cap.release()
cv2.destroyAllWindows()
