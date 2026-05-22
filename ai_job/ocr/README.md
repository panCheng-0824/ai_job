# PaddleOCR Demo

## 1) Install dependencies

Use your virtual environment first, then install:

```bash
pip install paddleocr
```

Install PaddlePaddle based on your machine from:

- https://www.paddlepaddle.org.cn/install/quick

Example (CPU):

```bash
pip install paddlepaddle
```

## 2) Run demo

```bash
python ocr/paddleocr_demo.py --image /absolute/path/to/your_image.png --use-angle-cls --lang ch
```

Or run as module:

```bash
python -m ocr.paddleocr_demo --image /absolute/path/to/your_image.png --use-angle-cls --lang ch
```

## 3) Optional JSON output

```bash
python ocr/paddleocr_demo.py --image /absolute/path/to/your_image.png --output-json ./ocr/result.json
```

## 4) Output format

Each recognized line includes:

- `text`: OCR text
- `score`: confidence
- `box`: detected bounding box coordinates

## 5) Module structure

- `ocr/models.py`: data models (`OCRSettings`, `OCRLine`)
- `ocr/core.py`: PaddleOCR initialization and OCR execution
- `ocr/cli.py`: argument parsing and settings building
- `ocr/paddleocr_demo.py`: CLI entry and output orchestration
