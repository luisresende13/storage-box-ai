let STORAGE_BOX_AI_API_URL = 'http://localhost:5000';
// const MONGO_API_URL = 'http://localhost:5000';
// const db = 'octacity';
// const coll = 'boxes';

let processingSeconds = 15;
let processingSleepSeconds = 3;
let processEach = 30;
let streamFps = 3;
let cameraFps = 30;
let confidence = 0.04
let getHistoryFps = 4
let getHistorySeconds = 1 / getHistoryFps

let processingFrames = (processingSeconds - processingSleepSeconds) * cameraFps + 1;
let streamEach = parseInt(cameraFps / streamFps);

let controller = new AbortController()

// Function to start the request
function startProcessing() {

    const cameraUrl = $('#camera-url').val();
    const markerSize = $('#marker-size').val();
    const inputConfidence = $('#confidence').val();
    const seconds = $('#seconds').val();
    if (seconds) {
        processingSeconds = parseInt(seconds)
        processingFrames = (processingSeconds - processingSleepSeconds) * cameraFps + 1
    }
    
    const { baseUrl, params: urlParams } = parseUrl(cameraUrl);

    console.log('baseUrl:', baseUrl)
    console.log('urlParams:', urlParams)
    console.log('markerSize:', markerSize)
    console.log('inputConfidence:', inputConfidence)
    console.log('processingSeconds:', processingSeconds)
    console.log('processingFrames:', processingFrames)

    const params = {
        url: baseUrl,
        max_frames: processingFrames,
        process_each: processEach,
        conf: confidence,
        yield_type: 'results',
        fill_results: 'frame-by-frame'
    };

    if (markerSize) {
        params['marker_size'] = markerSize
    }

    if (inputConfidence) {
        params['conf'] = inputConfidence
    }

    for (const [key, value] of Object.entries(urlParams)) {
        params[key] = value;
    }

    const queryString = objectToQueryString(params);
    const url = `${STORAGE_BOX_AI_API_URL}/process?${queryString}`;

    fetch(url, { signal: controller.signal })
        .then(response => {
            if (!response.ok) {
                throw new Error(`PROCESSING HTTP ERROR! | STATUS: ${response.status} | MESSAGE: ${response.statusText} | TEXT: ${response.text}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('PROCESSING SUCCESSFUL:', data);
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                console.log('PROCESSING WAS ABORTED');
            } else {
                console.error('PROCESSING ERROR:', error);
            }
        });

    console.log('PROCESSING STARTED...');
}

// Function to stop the request
function stopProcessing() {
    if (controller) {
        controller.abort();
    }
    controller = new AbortController()
}

function objectToQueryString(obj) {
    return Object.keys(obj).map(key => `${encodeURIComponent(key)}=${encodeURIComponent(obj[key])}`).join('&');
}

function getDetections(baseUrl) {
    const url = `${baseUrl}/boxes`;

    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} | message: ${response.statusText} | text: ${response.text}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
            return null;
        });
}

function parseUrl(url) {
    const urlPattern = /^(rtsp:\/\/[^\/]+)(\/[^?]+)(\?.+)?$/;
    const match = url.match(urlPattern);
    if (!match) {
        console.error('Invalid URL');
        return { baseUrl: url, params: {} };
    }
    const baseUrl = match[1] + match[2];
    const queryString = match[3] ? match[3].substring(1) : '';
    const params = {};
    if (queryString) {
        const pairs = queryString.split('&');
        pairs.forEach(pair => {
            const [key, value] = pair.split('=');
            params[key] = decodeURIComponent(value || '');
        });
    }
    return { baseUrl, params };
}

let detectionIds = [];

$(document).ready(function() {
    let cameraConnected = false;
    let detectionRunning = false;
    let detectionTime = null;
    let timePassedInterval = null;
    let detectionHistory = [];
    let lastConnectionTime = null;
    let lastMarkerDetectionTime = null;
    let connectionInterval = null;
    let detectionInterval = null;
    let processingInterval = null;
    let markerInterval = null;

    // connectCamera(resetConnectionTime=true)

    $('#connect-btn').click(function() {
        if (detectionRunning) {
            disconnectDetection()
        }

        connectCamera(resetConnectionTime=true);
    });

    $('#disconnect-btn').click(function() {
        if (detectionRunning) {
            disconnectDetection()
        }

        disconnectCamera();
    });

    $('#detect-btn').click(function() {
        connectDetection();
    });

    $('#stop-detect-btn').click(function() {
        disconnectDetection();
    });

    function disconnectCamera() {
        const stream = document.getElementById('camera-feed');
        stream.src = null;

        cameraConnected = false;
        $('#camera-status').text('Disconnected');        
        if (connectionInterval) {
            clearInterval(connectionInterval);
        }
        
        // $('#last-connection-time').text('N/A');
        // $('#time-since-connected').text('N/A');

    }
    
    function connectCamera(resetConnectionTime=true) {

        const cameraUrl = $('#camera-url').val();
        const markerSize = $('#marker-size').val();
        const inputConfidence = $('#confidence').val();
        const { baseUrl, params: urlParams } = parseUrl(cameraUrl);
    
        console.log('baseUrl:', baseUrl)
        console.log('urlParams:', urlParams)
        console.log('markerSize:', markerSize)
        console.log('inputConfidence:', inputConfidence)
            
        const params = {
            url: baseUrl,
            process_each: 1000000000,
            yield_each: streamEach,
            conf: confidence,
            yield_type: 'images',
            fill_results: 'none'
        };

        if (markerSize) {
            params['marker_size'] = markerSize
        }

        if (inputConfidence) {
            params['conf'] = inputConfidence
        }

        for (const [key, value] of Object.entries(urlParams)) {
            params[key] = value;
        }
        
        const queryString = objectToQueryString(params);
        const streamUrl = `${STORAGE_BOX_AI_API_URL}/process?${queryString}`;
        
        const stream = document.getElementById('camera-feed');
        stream.src = streamUrl;
    
        if (resetConnectionTime) {
            cameraConnected = true;
            $('#camera-status').text('Connected');
            lastConnectionTime = new Date();
            $('#last-connection-time').text(lastConnectionTime.toLocaleTimeString());
            updateConnectionTime();
            if (connectionInterval) {
                clearInterval(connectionInterval);
            }
            connectionInterval = setInterval(updateConnectionTime, 250);
        }    
    }

    function connectDetection() {
        startProcessing();

        const cameraUrl = $('#camera-url').val();
        const markerSize = $('#marker-size').val();
        const inputConfidence = $('#confidence').val();
        const { baseUrl, params: urlParams } = parseUrl(cameraUrl);

        console.log('baseUrl:', baseUrl)
        console.log('urlParams:', urlParams)
        console.log('markerSize:', markerSize)
        console.log('inputConfidence:', inputConfidence)
        
        const params = {
            url: baseUrl,
            process_each: processEach,
            yield_each: streamEach,
            conf: confidence,
            yield_type: 'images',
            fill_results: 'frame-by-frame'
        };

        if (markerSize) {
            params['marker_size'] = markerSize
        }

        if (inputConfidence) {
            params['conf'] = inputConfidence
        }

        for (const [key, value] of Object.entries(urlParams)) {
            params[key] = value;
        }

        const queryString = objectToQueryString(params);
        const streamUrl = `${STORAGE_BOX_AI_API_URL}/process?${queryString}`;
        
        const stream = document.getElementById('camera-feed');
        stream.src = streamUrl;
        
        startDetection();
    }

    function disconnectDetection() {
        connectCamera(resetConnectionTime=false)

        stopDetection();
    }

    function startDetection() {
        detectionRunning = true;

        // $('#processing-status').text('Running');
        processingInterval = setInterval(startProcessing, processingSeconds * 1000)

        $('#detection-status').text('Running');

        $('#marker-status').text('Running');
        lastMarkerDetectionTime = new Date();
        $('#last-marker-detection-time').text(lastMarkerDetectionTime.toLocaleTimeString());
        updateMarkerDetectionTime();
        if (markerInterval) {
            clearInterval(markerInterval);
        }
        markerInterval = setInterval(updateMarkerDetectionTime, 250);

        if (timePassedInterval) {
            clearInterval(timePassedInterval);
        }
        timePassedInterval = setInterval(updateTimePassed, 250);

        detectionInterval = setInterval(async () => {

            let detections = await getDetections(STORAGE_BOX_AI_API_URL);

            if (!detections.length) {
                console.log('NO DETECTIONS FOUND')
                return
            }
            
            detections.sort((a, b) => {
                return new Date(b.timestamp) - new Date(a.timestamp);
            });

            let lastDetection = detections[0];
            let boxes = lastDetection.objects;

            // detectionTime = new Date();
            detectionTime = new Date(lastDetection.timestamp);

            updateDetectionTime();
            updateTimePassed();

            boxes.forEach(box => {
                if (!box.has_dimensions) {
                    box.height = 0.0;
                    box.width = 0.0;
                    box.area_cm2 = 0.0;
                }
            });

            updateDetectionReport(boxes.length > 0, boxes);

            if (!detectionIds.includes(lastDetection._id)) {
                console.log(`New Detection: ${JSON.stringify(lastDetection)}`);
                detectionIds.push(lastDetection._id);
                addToDetectionHistory(detectionTime, boxes);
            }
        }, getHistorySeconds * 1000);
    }

    function stopDetection() {
        detectionRunning = false;
        $('#detection-status').text('Not Running');
        $('#marker-status').text('Not Running');
        // detectionTime = null;
        if (processingInterval) {
            clearInterval(processingInterval);
        }
        if (detectionInterval) {
            clearInterval(detectionInterval);
        }
        // if (timePassedInterval) {
            // clearInterval(timePassedInterval);
        // }
        if (markerInterval) {
            clearInterval(markerInterval);
        }
        // updateDetectionReport(false, []);
        
        // $('#detection-time').text('N/A');
        // $('#time-passed').text('N/A');
        // $('#last-marker-detection-time').text('N/A');
        // $('#time-since-last-marker-detection').text('N/A');
    }

    function updateDetectionReport(detected, boxes) {
        $('#box-detection').text(detected ? 'Yes' : 'No');
        $('#box-count').text(boxes.length);
        $('#box-details').empty();
        if (detected) {
            boxes.forEach(box => {
                $('#box-details').append(`
                    <tr>
                        <td>${box._id}</td>
                        <td>${box.width.toFixed(2)}</td>
                        <td>${box.height.toFixed(2)}</td>
                        <td>${box.area_cm2.toFixed(2)}</td>
                    </tr>
                `);
            });

            const summary = summarizeBoxes(boxes);
            $('#avg-width').text(summary.avgWidth);
            $('#std-dev-width').text(summary.stdDevWidth);
            $('#avg-height').text(summary.avgHeight);
            $('#std-dev-height').text(summary.stdDevHeight);
            $('#avg-area').text(summary.avgArea);
            $('#std-dev-area').text(summary.stdDevArea);
        } else {
            $('#avg-width').text('N/A');
            $('#std-dev-width').text('N/A');
            $('#avg-height').text('N/A');
            $('#std-dev-height').text('N/A');
            $('#avg-area').text('N/A');
            $('#std-dev-area').text('N/A');
        }
    }

    function updateDetectionTime() {
        if (detectionTime) {
            $('#detection-time').text(detectionTime.toLocaleTimeString());
        }
    }

    function updateTimePassed() {
        if (detectionTime) {
            const now = new Date();
            const timePassed = Math.floor((now - detectionTime) / 1000);
            $('#time-passed').text(formatTimePassed(timePassed));
        }
    }

    function updateConnectionTime() {
        if (lastConnectionTime) {
            const now = new Date();
            const timeConnected = Math.floor((now - lastConnectionTime) / 1000);
            $('#time-since-connection').text(formatTimePassed(timeConnected));
        }
    }

    function updateMarkerDetectionTime() {
        if (lastMarkerDetectionTime) {
            const now = new Date();
            const timeSinceMarkerDetected = Math.floor((now - lastMarkerDetectionTime) / 1000);
            $('#time-since-last-marker-detection').text(formatTimePassed(timeSinceMarkerDetected));
        }
    }

    function formatTimePassed(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours}h ${minutes}m ${secs}s`;
    }

    function addToDetectionHistory(time, boxes) {
        const summary = summarizeBoxes(boxes);
        detectionHistory.unshift({ time, ...summary });
        // detectionHistory.push({ time, ...summary });
        updateDetectionHistoryTable();
    }

    function summarizeBoxes(boxes) {
        const widthValues = boxes.map(box => box.width);
        const heightValues = boxes.map(box => box.height);
        const areaValues = boxes.map(box => box.area_cm2);

        const avgWidth = average(widthValues);
        const stdDevWidth = standardDeviation(widthValues, avgWidth);
        const avgHeight = average(heightValues);
        const stdDevHeight = standardDeviation(heightValues, avgHeight);
        const avgArea = average(areaValues);
        const stdDevArea = standardDeviation(areaValues, avgArea);

        return { 
            boxCount: boxes.length, 
            avgWidth, stdDevWidth, 
            avgHeight, stdDevHeight, 
            avgArea, stdDevArea 
        };
    }

    function average(values) {
        const sum = values.reduce((a, b) => a + b, 0);
        return (sum / values.length).toFixed(2);
    }

    function standardDeviation(values, mean) {
        const sqDiffs = values.map(value => Math.pow(value - mean, 2));
        const avgSqDiff = average(sqDiffs);
        return Math.sqrt(avgSqDiff).toFixed(2);
    }

    function updateDetectionHistoryTable() {
        $('#detection-history').empty();
        detectionHistory.forEach(entry => {
            $('#detection-history').append(`
                <tr>
                    <td>${entry.time.toLocaleTimeString()}</td>
                    <td>${entry.boxCount}</td>
                    <td>${entry.avgWidth}</td>
                    <td>${entry.stdDevWidth}</td>
                    <td>${entry.avgHeight}</td>
                    <td>${entry.stdDevHeight}</td>
                    <td>${entry.avgArea}</td>
                    <td>${entry.stdDevArea}</td>
                </tr>
            `);
        });
    }
});
