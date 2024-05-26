import cv2
import numpy as np
import time
from datetime import datetime
from modules.yolov5_wrap import YOLOV5Wrap
import traceback

# from object_detector import *

# def increase_contrast(frame, alpha=1.5, beta=50):
#     """
#     Increase the contrast of the frame.
#     :param frame: input frame
#     :param alpha: contrast control (1.0-3.0)
#     :param beta: brightness control (0-100)
#     :return: frame with increased contrast
#     """
#     adjusted = cv2.convertScaleAbs(frame, alpha=alpha)
#     return adjusted


def run_storage_box_dimension_camera(url, model, max_frames=30, process_each=30, yield_each=10, predict_params=dict(imgsz=640, conf=0.01, classes=[20], max_det=None), fill_results='frame-by-frame', filter_results='processed-only', yield_type='images'):

    # Load Aruco detector
    parameters = cv2.aruco.DetectorParameters()
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # Load Object Detector
    # detector = HomogeneousBgDetector()
    
    # Load Cap
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_FPS, 30)

    fid = None
    n_frames = 0
    n_frames_fps = 0
    fps_roll = 0.00
    t = time.time()
    fps = 0.00
    start_time = time.time()
    
    corners = None
    results = []
    objects = []
    
    timestamp_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        while True:

            if max_frames is not None and n_frames >= max_frames:
                break
            
            ret, img = cap.read()

            if not ret:
                raise Exception(f'ERROR READING FRAME | FID: {fid} | URL: {url}')

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            n_frames += 1
            n_frames_fps += 1
            fid = n_frames - 1

            # Get Aruco marker
            if fill_results == 'none':
                corners = None
            if fid % process_each == 0:
                corners, _, _ = aruco_detector.detectMarkers(img)
            
            pixel_cm_ratio = None
            if corners:
        
                # Draw polygon around the marker
                int_corners = np.int0(corners)
                cv2.polylines(img, int_corners, True, (0, 255, 0), 5)
        
                # Aruco Perimeter
                aruco_perimeter = cv2.arcLength(corners[0], True)
    
                # Pixel to cm ratio
                pixel_cm_ratio = aruco_perimeter / 20


            if fill_results == 'none':
                objects = []
            
            # elif fill_results == 'processed-only':
            #     # Do nothing
            
            if fid % process_each == 0:
                objects = model.predict(source=img, **predict_params) # 20: Storage box
        
            # objects = detector.detect_objects(img)
        
            # Draw objects boundaries
            for obj in objects:
        
                # Extract the coordinates
                x_min, y_min, x_max, y_max = obj['bbox']
        
                x = (x_max + x_min) / 2
                y = (y_max + y_min) / 2
                w = x_max - x_min
                h = y_max - y_min
                
                # Define the vertices of the bounding box
                box_points = np.array([
                    [x_min, y_min],  # Top-left
                    [x_max, y_min],  # Top-right
                    [x_max, y_max],  # Bottom-right
                    [x_min, y_max]   # Bottom-left
                ], dtype=np.float32)
                
                # Reshape to the required shape (n, 1, 2)
                box = box_points.reshape((-1, 1, 2)).astype(np.int32)
    
                obj['pixel_cm_ratio'] = pixel_cm_ratio
                obj['has_dimensions'] = False
                obj['width'] = None
                obj['height'] = None
                obj['area_cm2'] = None
    
                if corners:
    
                    # Get Width and Height of the Objects by applying the Ratio pixel to cm
                    object_width = w / pixel_cm_ratio
                    object_height = h / pixel_cm_ratio

                    obj['has_dimensions'] = True
                    obj['width'] = object_width
                    obj['height'] = object_height
                    obj['area_cm2'] = object_width * object_height
    
                    cv2.putText(img, "Width {} cm".format(round(object_width, 1)), (int(x - 100), int(y - 20)), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)
                    cv2.putText(img, "Height {} cm".format(round(object_height, 1)), (int(x - 100), int(y + 15)), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)
        
                cv2.circle(img, (int(x), int(y)), 5, (0, 0, 255), -1)
                cv2.polylines(img, [box], True, (255, 0, 0), 2)

            total_time = time.time() - start_time
            fps = round(n_frames / total_time, 2)
            fps_roll = round(n_frames_fps / (time.time() - t), 2)
            if n_frames % 150 == 0:
                t = time.time()
                n_frames_fps = 0

            if fid % yield_each == 0:
                cv2.putText(img, f"FPS: {fps_roll}/{fps}", (20, 20), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 0), 2)

            if yield_type == 'results':
                if filter_results == 'none' or (filter_results == 'processed-only' and fid % process_each == 0):
                    result = {'fid': fid, 'timestamp': timestamp, 'fps_roll': fps_roll, 'fps': fps, 'n_objects': len(objects), 'objects': objects}
                    results.append(result)
                    yield result

            elif yield_type == 'images':
                if fid % yield_each == 0:
                    # Encode the frame as JPEG
                    ret, jpeg = cv2.imencode('.jpg', img)
                    
                    if not ret:
                        raise Exception(f'ERROR DECODING FRAME | FID: {fid} | URL: {url}')
            
                    # Convert the JPEG image to bytes and yield it
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                    
                    # cv2.imshow("Image", img)
                    # key = cv2.waitKey(1)
                    # if key == 27:
                        # break

        return results
        
    except Exception as e:
        print(f'Error: {traceback.format_exc()}')

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    # url = 0
    url = 'rtsp://admin:141291@octateste.ddns-intelbras.com.br:554/cam/realmonitor?channel=4&subtype=0'
    max_frames = 300
    process_each = 90
    yield_each = 30
    model = YOLOV5Wrap(path='models/yolov5m_Objects365.pt') # 'yolov5s' # or 'objects365'
    predict_params = dict(imgsz=640, conf=0.001, classes=[20], max_det=None)
    fill_results = 'none'
    filter_results = 'none'
    yield_type = 'results'
    
    results = run_storage_box_dimension_camera(url, model, max_frames, process_each, yield_each, predict_params, fill_results, filter_results, yield_type)

