# Hybrid PDF Parser - Гибридный парсер PDF документов

## Описание

`hybrid_pdf_parser.py` - это интеллектуальный парсер PDF документов, который сочетает в себе возможности GROBID (для структурированного извлечения текста) и PyMuPDF (для fallback извлечения). Парсер автоматически выбирает наиболее подходящий метод для каждого документа, обеспечивая максимальное покрытие и качество извлечения.

## Ключевые возможности
Парсер работает гибридно, работает сначала GROBID, затем запасной эвристический парсер. Как правило, отрабатывает только GROBID, документы с ошибками - сканы текста. Каждая статья сохраняется в отдельный JSON файл, поддержка извлечения аннотации.

## Архитектура

```
HybridPDFParser
├── parse_article() - Основной метод парсинга
├── parse_pdf_to_xml() - GROBID API интеграция
├── extract_from_xml() - Парсинг TEI XML от GROBID
├── extract_text_with_pymupdf() - Fallback PyMuPDF извлечение
└── extract_text_from_element() - Вспомогательный метод для XML
```

## Требования

- Python 3.7+
- GROBID сервер (Docker)
- PyMuPDF (fitz)
- requests

## Установка

### 1. Установка зависимостей

```bash
pip install -r requirements_hybrid_parser.txt
```

### 2. Запуск GROBID сервера

```bash
# Запуск в Docker
docker run -d --name grobid-server -p 8070:8070 lfoppiano/grobid:0.7.3

# Проверка статуса
curl http://localhost:8070/api/isalive
```

## Использование

### Базовый запуск

```bash
python hybrid_pdf_parser.py
```

### Структура входных данных

```
pages/
└── Компьютерные и информационные науки/
    ├── article1.pdf
    ├── article2.pdf
    └── ...
```

### Структура выходных данных

```
extracted_articles/
├── all_articles.json          # Все статьи в одном файле
├── parsing_statistics.json    # Статистика обработки
├── Название_статьи_GROBID.json    # Индивидуальные файлы
└── Название_статьи_PyMuPDF.json
```

## Формат выходных данных

### Структура JSON для каждой статьи

```json
{
  "filename": "название_файла.pdf",
  "title": "название_статьи",
  "abstract": "текст_абстракта",
  "full_text": "полный_текст_статьи",
  "abstract_length": 1234,
  "text_length": 56789,
  "method": "GROBID|PyMuPDF"
}
```

### Статистика обработки

```json
{
  "total_files": 100,
  "successful": 95,
  "grobid_success": 80,
  "pymupdf_success": 15,
  "failed": 5,
  "success_rate": "95.0%"
}
```


## Настройка

### Изменение GROBID URL

```python
parser = HybridPDFParser(grobid_url="http://your-grobid-server:8070")
```

### Настройка таймаутов

```python
# В методе parse_pdf_to_xml
response = requests.post(..., timeout=120)  # Увеличить таймаут
```

### Изменение директории входных файлов

```python
# В функции main()
input_dir = Path("your/path/to/pdfs")
```



## Примеры использования

### Обработка одного файла

```python
from hybrid_pdf_parser import HybridPDFParser

parser = HybridPDFParser()
result = parser.parse_article(Path("article.pdf"))
print(f"Метод: {result['method']}")
print(f"Абстракт: {result['abstract'][:100]}...")
```

