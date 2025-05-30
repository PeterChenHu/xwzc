#!/bin/bash
import cv2
import subprocess
import os
import time
import json
from datetime import datetime
from ultralytics import YOLO
from flask_cors import CORS, cross_origin
from multiprocessing import Process, Manager
from flask import Flask, request, jsonify, url_for, send_from_directory


CAMERA_CONFIGS = [
    {"cam_id": "cam01", "rtsp_url": "rtsp://admin:xwzc2025@192.168.1.64/H264/Streaming/Channels/101"},
    # Add more cameras as needed
]

STATIC_FOLDER = "static/videos"
# process_manager = Manager()
# camera_processes = process_manager.dict()
camera_processes = {}

app = Flask(__name__, static_folder=STATIC_FOLDER)
CORS(app)

def cleanup_camera_processes():
    to_remove = []
    for key, proc in camera_processes.items():
        if not proc.is_alive():
            to_remove.append(key)
    for key in to_remove:
        del camera_processes[key]

def run_cv_model(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(processed, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    detections = []
    return processed, detections

def camera_worker(cam_id, rtsp_url):
    hls_folder = os.path.join(STATIC_FOLDER, f"{cam_id}_hls")
    os.makedirs(hls_folder, exist_ok=True)
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"[{cam_id}] Failed to open RTSP stream")
        return
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", "15",
        "-i", "-",
        "-c:v", "h264_rkmpp",
        "-b:v", "5M",
        "-f", "hls",
        "-hls_time", "1",
        "-hls_list_size", "30",
        "-hls_flags", "delete_segments+append_list",
        "-hls_segment_filename", os.path.join(hls_folder, "segment_%06d.ts"),
        os.path.join(hls_folder, "index.m3u8")
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[{cam_id}] Frame grab failed, retrying...")
                time.sleep(1)
                continue
            ffmpeg_proc.stdin.write(frame.tobytes())
            time.sleep(0.01)
    except Exception as e:
        print(f"[{cam_id}] Worker error: {e}")
    finally:
        cap.release()
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()

def get_rtsp_url(cam_id):
    for cam in CAMERA_CONFIGS:
        if cam["cam_id"] == cam_id:
            return cam["rtsp_url"]
    return None

@cross_origin()
@app.route('/stream/<cam_id>/<timestamp>', methods=['GET'])
def transcode_rtsp_to_hls(cam_id, timestamp):
    cleanup_camera_processes()
    if not cam_id or not timestamp:
        return jsonify({'error': 'Missing camera_id or timestamp'}), 400

    # Only start if not already running
    if cam_id not in camera_processes or not camera_processes[cam_id].is_alive():
        rtsp_url = get_rtsp_url(cam_id)
        if not rtsp_url:
            return jsonify({'error': 'Camera not found'}), 404
        p = Process(target=camera_worker, args=(cam_id, rtsp_url))
        p.daemon = True
        p.start()
        camera_processes[cam_id] = p

    hls_url = f"/videos/{cam_id}_hls/index.m3u8"
    full_url = url_for('static', filename=f"{cam_id}_hls/index.m3u8", _external=True)
    return jsonify({
        'hls_path': hls_url,         
        'hls_url': full_url,         
        'timestamp': timestamp,
        'cam_id': cam_id,
        'status': 'streaming'
    })

def camera_worker_flv(cam_id, rtsp_url):
    cleanup_camera_processes()
    flv_folder = os.path.join(STATIC_FOLDER, f"{cam_id}_flv")
    os.makedirs(flv_folder, exist_ok=True)
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"[{cam_id}] Failed to open RTSP stream")
        return
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", "15",
        "-i", "-",
        "-c:v", "h264_rkmpp",
        "-b:v", "5M",
        "-f", "flv",
        os.path.join(flv_folder, f"{cam_id}.flv")
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[{cam_id}] Frame grab failed, retrying...")
                time.sleep(1)
                continue
            ffmpeg_proc.stdin.write(frame.tobytes())
            time.sleep(0.01)
    except Exception as e:
        print(f"[{cam_id}] FLV Worker error: {e}")
    finally:
        cap.release()
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()

def camera_worker_cv(cam_id, rtsp_url):
    model = YOLO("yolo11x-seg.pt")
    cv_hls_folder = os.path.join(STATIC_FOLDER, f"{cam_id}_cv_hls")
    os.makedirs(cv_hls_folder, exist_ok=True)
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"[{cam_id}] Failed to open RTSP stream")
        return
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", "15",
        "-i", "-",
        "-c:v", "h264_rkmpp",
        "-b:v", "5M",
        "-f", "hls",
        "-hls_time", "1",
        "-hls_list_size", "30",
        "-hls_flags", "delete_segments+append_list",
        "-hls_segment_filename", os.path.join(cv_hls_folder, "segment_%06d.ts"),
        os.path.join(cv_hls_folder, "index.m3u8")
    ]
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[{cam_id}] Frame grab failed, retrying...")
                time.sleep(1)
                continue
            
            results = model.predict(source=frame, conf=0.4)
            annotated_frame = results[0].plot()
            ffmpeg_proc.stdin.write(annotated_frame.tobytes())
            time.sleep(0.01)
    except Exception as e:
        print(f"[{cam_id}] CV Worker error: {e}")
    finally:
        cap.release()
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()

@cross_origin()
@app.route('/stream_flv/<cam_id>/<timestamp>', methods=['GET'])
def stream_flv(cam_id, timestamp):
    cleanup_camera_processes()
    if not cam_id or not timestamp:
        return jsonify({'error': 'Missing camera_id or timestamp'}), 400
    key = f"{cam_id}_flv"
    if key not in camera_processes or not camera_processes[key].is_alive():
        rtsp_url = get_rtsp_url(cam_id)
        if not rtsp_url:
            return jsonify({'error': 'Camera not found'}), 404
        p = Process(target=camera_worker_flv, args=(cam_id, rtsp_url))
        p.daemon = True
        p.start()
        camera_processes[key] = p
    flv_url = f"/videos/{cam_id}_flv/{cam_id}.flv"
    full_url = url_for('static', filename=f"{cam_id}_flv/{cam_id}.flv", _external=True)
    return jsonify({
        'flv_path': flv_url,
        'flv_url': full_url,
        'timestamp': timestamp,
        'cam_id': cam_id,
        'status': 'streaming'
    })

@cross_origin()
@app.route('/stream_cv/<cam_id>/<timestamp>', methods=['GET'])
def stream_cv(cam_id, timestamp):
    cleanup_camera_processes()
    if not cam_id or not timestamp:
        return jsonify({'error': 'Missing camera_id or timestamp'}), 400
    key = f"{cam_id}_cv"
    if key not in camera_processes or not camera_processes[key].is_alive():
        rtsp_url = get_rtsp_url(cam_id)
        if not rtsp_url:
            return jsonify({'error': 'Camera not found'}), 404
        p = Process(target=camera_worker_cv, args=(cam_id, rtsp_url))
        p.daemon = True
        p.start()
        camera_processes[key] = p
    hls_url = f"/videos/{cam_id}_cv_hls/index.m3u8"
    full_url = url_for('static', filename=f"{cam_id}_cv_hls/index.m3u8", _external=True)
    return jsonify({
        'hls_path': hls_url,
        'hls_url': full_url,
        'timestamp': timestamp,
        'cam_id': cam_id,
        'status': 'cv_streaming'
    })

@app.route('/videos/<path:filename>')
@cross_origin()
def custom_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == '__main__':
    os.makedirs(STATIC_FOLDER, exist_ok=True)
    app.run(host="0.0.0.0", debug=True) #ssl_context=('cert.pem', 'key.pem'), port=5000)
