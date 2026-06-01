# MedCore test ajilluulah alhmuud

Энэ файл нь backend test, frontend lint/build, GitHub Actions-тэй ижил CI шалгалтуудыг local дээр ажиллуулах дараалал юм.

## 1. Project root руу орох

```bash
cd /home/tontoosh/Desktop/medcore/code/MedCore
```

## 2. Backend virtual environment үүсгэх

Анх удаа ажиллуулж байгаа бол:

```bash
python3 -m venv backend/.venv
```

Хэрэв `backend/.venv` аль хэдийн байгаа бол энэ алхмыг алгасаж болно.

## 3. Backend dependency суулгах

```bash
backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements-dev.txt
```

`requirements.txt` нь production backend dependency. `requirements-dev.txt` нь түүн дээр нэмээд `pytest`, `httpx` зэрэг test dependency-г суулгана.

## 4. OCR language байгаа эсэхийг шалгах

```bash
tesseract --list-langs
```

Local дээр дор хаяж эд нар байх ёстой:

```text
eng
mon
```

Ubuntu дээр байхгүй бол:

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-mon
```

## 5. Backend бүх test ажиллуулах

```bash
backend/.venv/bin/python -m pytest backend/tests
```

Зөвхөн нэг test file ажиллуулах жишээ:

```bash
backend/.venv/bin/python -m pytest backend/tests/test_patient_portal_api.py
```

Дэлгэрэнгүй output харах:

```bash
backend/.venv/bin/python -m pytest backend/tests -vv
```

## 6. Frontend dependency суулгах

```bash
npm ci
```

## 7. Frontend lint шалгах

```bash
npm run lint
```

## 8. Frontend build шалгах

```bash
npm run build
```

## 9. CI-тэй адил бүгдийг дарааллаар ажиллуулах

```bash
backend/.venv/bin/python -m pytest backend/tests
npm ci
npm run lint
npm run build
```

## 10. GitHub Actions

Workflow файл:

```text
.github/workflows/ci.yml
```

GitHub дээр `push` эсвэл `pull_request` хийхэд автоматаар:

1. Python 3.13 суулгана
2. Node 22 суулгана
3. Tesseract OCR болон `eng`, `mon` language package суулгана
4. Backend dependency суулгана
5. `pytest` ажиллуулна
6. `npm ci` ажиллуулна
7. `npm run lint` ажиллуулна
8. `npm run build` ажиллуулна

## 11. Local дээр TestClient гацвал

Зарим sandbox орчинд FastAPI sync endpoint test нь `TestClient` threadpool дээр гацаж болно. Тийм үед эхлээд service-level test ажиллаж байгаа эсэхийг шалгана:

```bash
backend/.venv/bin/python -m pytest backend/tests/test_ai_service.py backend/tests/test_storage_ocr_security.py -vv
```

GitHub Actions-ийн Ubuntu runner дээр workflow нь `.github/workflows/ci.yml`-ийн дагуу бүрэн test suite ажиллуулна.
