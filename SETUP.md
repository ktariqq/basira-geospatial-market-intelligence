# Basira Setup Guide

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Download models (one-time, ~500MB total)
```bash
python -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
m.save('models/multilingual-minilm')
print('Classifier model saved.')
"

python -c "
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8', download_root='models/whisper-small')
print('Whisper model saved.')
"
```

## 3. Verify data files
```bash
bash data_download.sh
```

## 4. Pre-compute demand scores
```bash
python scripts/compute_demand.py --community alquaa
```

## 5. Run
```bash
# Web UI (recommended)
python basira.py

# CLI with text
python basira.py --text "أريد تربية الإبل وبيع الحليب"

# CLI with voice
python basira.py --voice

# Different port
python basira.py --port 8080
```

Open http://localhost:8000
