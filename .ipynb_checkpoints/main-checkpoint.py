'''
TO-DO:

    1. Update report section to support dimensions of each detected box
    1. Add Time since last detection in the report
    2. Add the time that the camera connected in the camera information section
    3. Add the time the marker is connected in the camera information section
    4. Add a detection history section with number of boxes and average 
    
'''

from time import time; t = time()
import json
from urllib.parse import urlencode
import uuid

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from modules.yolov5_wrap import YOLOV5Wrap
from modules.box_dimension import run_storage_box_dimension_camera  # Import your specific modules/functions
from modules.mongo_api_http import MongoDB

MONGO_API_URL = 'http://localhost:5001'
mongo = MongoDB(MONGO_API_URL)

model = YOLOV5Wrap(path='models/yolov5m_Objects365.pt') # 'yolov5s' # or 'objects365'

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*")

boxes = []

@app.route('/')
def index():
    return render_template('index.html')
    
@socketio.on('process')
def handle_start_process(data):
    
    url = data.get('url', 1)
    max_frames = int(data.get('max_frames', 301))
    process_each = int(data.get('process_each', 90))
    yield_each = int(data.get('yield_each', 1))
    yield_type = data.get('yield_type', 'images')
    
    imgsz = int(data.get('imgsz', 640))
    conf = float(data.get('conf', 0.001))
    classes = list(map(int, data.get('classes', '20').split(',')))
    max_det = data.get('max_det', None)
    fill_results = data.get('fill_results', 'frame-by-frame')
    filter_results = data.get('filter_results', 'processed-only')

    if max_det is not None:
        max_det = int(max_det)
        
    if yield_each is not None:
        yield_each = int(yield_each)

    print(f'PROCESS REQUEST | URL: {url} | MAX_FRAMES: {max_frames} | PROCESS_EACH: {process_each} | YIELD_EACH: {yield_each} | IMGSZ: {imgsz} | CONF: {conf} | CLASSES: {classes} | MAX_DET: {max_det} | FILL_RESULTS: {fill_results} | FILTER_RESULTS: {filter_results}')

    predict_params = dict(imgsz=imgsz, conf=conf, classes=classes, max_det=max_det)

    results = run_storage_box_dimension_camera(url, model, max_frames, process_each, yield_each, predict_params, fill_results, filter_results, yield_type)

    if yield_type == 'images':
        for frame in results:
            socketio.emit('frame', {'data': frame})

@app.route('/boxes', methods=['GET'])
def get_boxes():
    return jsonify(boxes)
    # return jsonify(json.load(open('boxes.json', 'r')))

@app.route('/process', methods=['GET'])
def process():
    global boxes
    args = request.args
    
    # Get query parameters
    url = args.get('url')
    # url = args.get('url', 'rtsp://admin:141291@octateste.ddns-intelbras.com.br:554/cam/realmonitor?channel=4&subtype=0')
    max_frames = args.get('max_frames', None)
    process_each = int(args.get('process_each', 90))
    yield_each = args.get('yield_each', 1)
    yield_type = args.get('yield_type', 'images')
    
    # Optional predict_params, if not provided, use defaults
    imgsz = int(args.get('imgsz', 640))
    conf = float(args.get('conf', 0.001))
    classes = list(map(int, args.get('classes', '20').split(',')))
    max_det = args.get('max_det', None)
    fill_results = args.get('fill_results', 'frame-by-frame')
    filter_results = args.get('filter_results', 'processed-only')
    marker_size = args.get('marker_size', None)

    if url is None:
        return 'Missing required parameter: `url`', 400

    params = ['url', 'max_frames', 'process_each', 'yield_each', 'yield_type', 'imgsz', 'conf', 'classes', 'max_det', 'fill_results', 'filter_results', 'marker_size']

    url_params = {}
    for key in args.keys():
        value = args.get(key)
        if key not in params and value is not None:
            url_params[key] = value

    if url_params:
        if '?' not in url:
            url += '?'
        url += urlencode(url_params)
            
    if url.isdigit():
        url = int(url)

    if max_frames is not None:
        max_frames = int(max_frames)

    if max_det is not None:
        max_det = int(max_det)
        
    if yield_each is not None:
        yield_each = int(yield_each)

    if marker_size is not None:
        marker_size = int(marker_size)

    # Print the parameters using an f-string
    print(f'\nPROCESSING STARTED | URL: {url} | MAX_FRAMES: {max_frames} | PROCESS_EACH: {process_each} | YIELD_EACH: {yield_each} | IMGSZ: {imgsz} | CONF: {conf} | CLASSES: {classes} | MAX_DET: {max_det} | FILL_RESULTS: {fill_results} | FILTER_RESULTS: {filter_results}')

    # Create model instance
    # model = YOLOV5Wrap(path='models/yolov5m_Objects365.pt') # 'yolov5s' # or 'objects365'
    
    # Define predict parameters
    predict_params = dict(imgsz=imgsz, conf=conf, classes=classes, max_det=max_det)

    start = time()

    # Run the function and get results
    results = run_storage_box_dimension_camera(url, model, max_frames, process_each, yield_each, predict_params, fill_results, filter_results, yield_type, marker_size)

    if yield_type == 'results':
        # Iterate the generator
        data = []
        for result in results:
            _id = uuid.uuid4()
            result['_id'] = str(_id)

            for obj in result['objects']:
                _id = uuid.uuid4()
                obj['_id'] = _id
            
            boxes = [result]
            # with open('boxes.json', 'w') as fw:
                # fw.write(json.dumps([result]))
                
            # mongo.delete_records("octacity", "boxes")
            # created = mongo.create_records("octacity", "boxes", result)

            # if 'error' in created:
                # print(f'\nERROR POSTING BOX DETECTION RESULTS TO MONGO: {created}')

            data.append(result)

        seconds = round(time() - start, 3)
        n_frames = len(data)
        fps = round(n_frames / seconds, 2)
        print(f'\nRESULTS PROCESSING FINISHED | N-FRAMES: {n_frames} | TIME: {seconds} s | FPS: {fps}')
        
        # Return the results as JSON
        return jsonify(data)

    elif yield_type == 'images':
        return Response(results, mimetype='multipart/x-mixed-replace; boundary=frame')

load_time = round(time() - t, 3)
print(f'\nAPP STARTED | LOAD-TIME: {load_time} s')

if __name__ == '__main__':
    app.run(debug=True)
    # socketio.run(app, host='0.0.0.0', port=5000, debug=True)
