# Tesseract Installation Guide — OCR for Scanned PDF Forms

## Overview

Tesseract is an open-source OCR (Optical Character Recognition) engine needed to extract handwritten text from scanned PDF forms. Without it, the adapter can still read **fillable PDF forms** but cannot process **scanned/handwritten forms**.

---

## Do I Need It?

**You NEED Tesseract if:**
- ✅ You want to import scanned PDF forms (paper forms, handwritten assessments)
- ✅ You want OCR text extraction from images

**You DON'T need Tesseract if:**
- ✅ You only use CSV/Excel exports
- ✅ You only use JSON imports
- ✅ You only use fillable PDF forms (digital, Adobe-created)

---

## Installation by Platform

### **macOS**

```bash
# Using Homebrew (easiest)
brew install tesseract

# Verify installation
tesseract --version
# Output: tesseract 5.x.x
```

### **Linux/Ubuntu**

```bash
# Install Tesseract
sudo apt-get update
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
# Output: tesseract 5.x.x
```

### **Windows**

1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer (select language during installation)
3. Note installation path (default: `C:\Program Files\Tesseract-OCR`)
4. Verify:
   ```bash
   tesseract --version
   ```

---

## Python Setup

### **Step 1: Install Python package**

```bash
pip install pytesseract pillow
```

### **Step 2: Configure pytesseract (Windows only)**

If Tesseract isn't in your PATH, tell pytesseract where it is:

```python
# In your Python script or .env
import pytesseract
pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Or set environment variable:
```bash
export PYTESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### **Step 3: Test installation**

```bash
python3 << 'EOF'
import pytesseract
print("✅ pytesseract imported successfully")

try:
    # Quick OCR test
    from PIL import Image
    import io
    
    # Create simple test image (10x10 white)
    img = Image.new('RGB', (10, 10), color='white')
    text = pytesseract.image_to_string(img)
    print("✅ Tesseract OCR working")
except Exception as e:
    print(f"❌ Tesseract error: {e}")
    print("   Make sure tesseract binary is installed and in PATH")
EOF
```

---

## Troubleshooting

### **Error: "tesseract is not installed or it's not in your PATH"**

**Cause:** Tesseract binary not found

**Solutions:**

1. **Verify installation:**
   ```bash
   which tesseract          # macOS/Linux
   where tesseract.exe      # Windows
   ```

2. **Add to PATH (if not automatic):**

   **macOS/Linux:**
   ```bash
   export PATH="/usr/local/bin:$PATH"
   # Or permanently in ~/.bashrc or ~/.zshrc
   ```

   **Windows:**
   ```bash
   set PATH=%PATH%;C:\Program Files\Tesseract-OCR
   # Or use System Environment Variables GUI
   ```

3. **Explicitly configure in Python:**
   ```python
   import pytesseract
   pytesseract.pytesseract.pytesseract_cmd = r'/usr/local/bin/tesseract'
   ```

### **Error: "No pytesseract module"**

```bash
pip install pytesseract pillow
```

### **Error: "No module named PIL"**

```bash
pip install pillow
```

---

## Verification Checklist

```bash
# ✅ Check 1: Tesseract binary installed
tesseract --version

# ✅ Check 2: pytesseract Python package
python3 -c "import pytesseract; print('OK')"

# ✅ Check 3: PIL/Pillow
python3 -c "from PIL import Image; print('OK')"

# ✅ Check 4: Can import adapter
python3 -c "from app.adapters.ingestors.pdf_ingestor import PDFFormIngestor; print('OK')"

# All checks pass? You're ready!
```

---

## Testing OCR with Sample Scanned Form

Once installed, test with a scanned PDF:

```bash
# Make sure ML service is running
make ml-dev

# Upload a scanned form
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@scanned_assessment.pdf" \
  -F "agency_name=Test Agency"

# If successful, response should include:
# {
#   "success": true,
#   "records_normalized": 1,
#   "mapping_confidence": 0.80-0.90
# }

# If Tesseract missing, you'll see:
# "error": "No data could be extracted from PDF"
```

---

## Performance Notes

### **OCR Processing Time**

| Pages | Time | Notes |
|-------|------|-------|
| 1 | ~3 sec | Quick |
| 5 | ~15 sec | Medium |
| 10 | ~30 sec | Slow |
| 50+ | 2-5 min | Very slow |

**Tips to speed up:**
- Scan at 200 DPI instead of 300 (faster, still readable)
- Process forms in batches of 5-10
- Run OCR on background workers for large batches

### **Accuracy Notes**

| Condition | Accuracy | Notes |
|-----------|----------|-------|
| Clear printed text | 99% | Best case |
| Legible handwriting | 85-95% | Depends on handwriting quality |
| Mixed printed/handwritten | 80-90% | Good enough |
| Poor handwriting | 50-70% | May need review |
| Cursive | 70-85% | Varies |

---

## For Different Development Setups

### **Local Development (no Docker)**

```bash
# 1. Install Tesseract
brew install tesseract     # macOS
# or
sudo apt install tesseract-ocr   # Linux

# 2. Install Python packages
pip install pytesseract pillow

# 3. Run ML service
make ml-dev

# 4. Test with PDF
curl -X POST http://localhost:8000/adapter/import \
  -F "file=@form.pdf" \
  -F "agency_name=Test"
```

### **Docker Compose**

If using Docker, add Tesseract to the ml-service Dockerfile:

```dockerfile
# Dockerfile (ml/Dockerfile)
FROM python:3.11-slim

# Install Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# Rest of Dockerfile...
COPY requirements.txt .
RUN pip install -r requirements.txt
```

Then rebuild:
```bash
make build-images
make docker-up
```

### **Kubernetes**

Add to ML service deployment.yaml:

```yaml
# k8s/ml-service/deployment.yaml
spec:
  containers:
  - name: ml-service
    image: dilly-dell-e/ml-service:latest
    # ... other config ...
    
# Or in pod spec, pre-install:
initContainers:
- name: install-tesseract
  image: python:3.11-slim
  command: 
    - sh
    - -c
    - apt-get update && apt-get install -y tesseract-ocr
```

---

## Optional: Tesseract Language Packs

By default, Tesseract supports English. For other languages:

**macOS:**
```bash
brew install tesseract-lang  # All languages
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr-all  # All languages
# Or specific:
sudo apt-get install tesseract-ocr-chi-sim  # Simplified Chinese
sudo apt-get install tesseract-ocr-ara      # Arabic
```

Then in Python:
```python
# OCR with specific language
pytesseract.image_to_string(img, lang='chi_sim')  # Chinese
pytesseract.image_to_string(img, lang='ara')      # Arabic
pytesseract.image_to_string(img, lang='eng+chi_sim')  # Multiple
```

---

## Summary

| Component | Status | Install |
|-----------|--------|---------|
| ML service | ✅ Ready | Already installed |
| CSV/Excel support | ✅ Ready | Already installed |
| JSON support | ✅ Ready | Already installed |
| PDF AcroForm | ✅ Ready | Already installed |
| PDF OCR (scanned) | ❌ Needs setup | Run: `brew install tesseract` |

**Next step:** Install Tesseract to enable OCR for scanned forms

---

## Getting Help

If still having issues:

1. Run verification checklist above
2. Check `docs/PDF_FORM_SUPPORT.md` for PDF-specific help
3. Check logs: `make ml-dev` shows detailed errors
4. Verify file permissions: Tesseract needs read access to image files

---

**Ready to OCR?** ✅ Install Tesseract and upload your scanned forms!
