# Menggunakan base image Python ringan
FROM python:3.11-slim

# Mencegah Python menulis file .pyc dan memastikan log output langsung tampil
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Menentukan direktori kerja di dalam container
WORKDIR /app

# Menginstal dependensi sistem untuk PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Menyalin dan menginstal dependensi Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Menyalin seluruh kode sumber (termasuk file dokumen produksi dan film) ke dalam container
COPY . /app/

# Membuka port 8000 untuk HTTP/JSON
EXPOSE 8000

# Menjalankan server aplikasi
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]