#!/bin/bash
STREAMS_CONFIG="streams.txt"
while IFS= read -r line; do
 if [ -n "$line" ]; then
 input_rtsp=$(echo "$line" | cut -d',' -f1)
 output_path=$(echo "$line" | cut -d',' -f2)
 output_rtsp="rtsp://132.232.216.60/$output_path"
 ffmpeg_cmd="ffmpeg -re -i $input_rtsp -vcodec copy -acodec aac -f rtsp -rtsp_transport tcp $output_rtsp"
 echo "Starting stream: $input_rtsp -> $output_rtsp"
 $ffmpeg_cmd &

 sleep 0.2
 fi
done < "$STREAMS_CONFIG"