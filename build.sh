#!/usr/bin/env bash
set -o errexit

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "📁 Creating YOLO models directory..."
mkdir -p yolo_models

echo "⬇️  Downloading YOLOv8n model..."
cd yolo_models
if [ ! -f "yolov8n.pt" ]; then
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
    echo "✅ YOLOv8n downloaded"
else
    echo "✅ YOLOv8n already exists"
fi
cd ..

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build completed!"