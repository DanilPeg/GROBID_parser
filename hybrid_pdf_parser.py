import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional
import logging
import time
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridPDFParser:
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        self.grobid_url = grobid_url
        
    def extract_text_with_pymupdf(self, pdf_path: Path) -> Dict:
        """Извлекает текст с помощью PyMuPDF - запасной вариант, для страниц где grobid ошибается"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    full_text += text + "\n"
            
            doc.close()
            
            # Ищем абстракт (обычно в начале документа)
            lines = full_text.split('\n')
            abstract = ""
            
            # Ищем строки, которые могут быть абстрактом
            for i, line in enumerate(lines[:20]):  # Первые 20 строк
                line = line.strip()
                if line and len(line) > 50:  # Длинные строки могут быть абстрактом
                    abstract += line + " "
                    if len(abstract) > 500:  
                        break
            
            return {
                "abstract": abstract.strip(),
                "full_text": full_text.strip()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста с PyMuPDF: {e}")
            return {"abstract": "", "full_text": ""}
    
    def parse_pdf_to_xml(self, pdf_path: Path) -> Optional[str]:
        """Парсит PDF файл через GROBID"""
        try:
            with open(pdf_path, 'rb') as f:
                files = {'input': (pdf_path.name, f, 'application/pdf')}
                data = {
                    'consolidateHeader': '1',
                    'consolidateCitations': '1',
                    'generateIDs': '1',
                    'includeRawCitations': '1',
                    'includeRawAffiliations': '1',
                    'teiCoordinates': '1'
                }
                
                response = requests.post(
                    f"{self.grobid_url}/api/processFulltextDocument",
                    files=files,
                    data=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"GROBID вернул ошибку {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при парсинге {pdf_path}: {e}")
            return None
    
    def extract_text_from_element(self, element) -> str:
        """Извлекает весь текст из элемента и его дочерних элементов"""
        if element is None:
            return ""
        
        text_parts = []
        for elem in element.iter():
            if elem.text and elem.text.strip():
                text_parts.append(elem.text.strip())
        return " ".join(text_parts)
    
    def extract_from_xml(self, xml_content: str) -> Dict:
        """Извлекает абстракт и полный текст из XML результата GROBID"""
        try:
            root = ET.fromstring(xml_content)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            abstract = ""
            abstract_elem = root.find('.//tei:profileDesc/tei:abstract', ns)
            if abstract_elem is not None:
                abstract = self.extract_text_from_element(abstract_elem)
            
            full_text = ""
            body_elem = root.find('.//tei:body', ns)
            if body_elem is not None:
                full_text = self.extract_text_from_element(body_elem)
            
            return {
                "abstract": abstract,
                "full_text": full_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных из XML: {e}")
            return {"abstract": "", "full_text": ""}
    
    def parse_article(self, pdf_path: Path) -> Optional[Dict]:
        """Парсинг одной статьи с fallback на PyMuPDF"""
        logger.info(f"Обрабатываю: {pdf_path.name}")
        
        # Сначала пробуем GROBID
        xml_content = self.parse_pdf_to_xml(pdf_path)
        
        if xml_content:
            
            extracted_data = self.extract_from_xml(xml_content)
            method = "GROBID"
        else:
            logger.info(f"GROBID не смог обработать {pdf_path.name}, пробуем PyMuPDF")
            extracted_data = self.extract_text_with_pymupdf(pdf_path)
            method = "PyMuPDF"
        
        # Проверяем, что получили хоть какой-то текст
        if not extracted_data["abstract"] and not extracted_data["full_text"]:
            logger.warning(f"Не удалось извлечь текст из {pdf_path.name}")
            return None
        
        result = {
            "filename": pdf_path.name,
            "title": pdf_path.stem,
            "abstract": extracted_data["abstract"],
            "full_text": extracted_data["full_text"],
            "abstract_length": len(extracted_data["abstract"]),
            "text_length": len(extracted_data["full_text"]),
            "method": method
        }
        
        return result

def main():
    parser = HybridPDFParser()
    
    output_dir = Path("extracted_articles")
    output_dir.mkdir(exist_ok=True)
    
    print("Начинаем гибридный парсинг PDF...")
    print(f"Результаты будут сохранены в: {output_dir}")
    
    input_dir = Path("pages/Компьютерные и информационные науки")
    pdf_files = list(input_dir.glob("*.pdf"))
    
    results = []
    grobid_success = 0
    pymupdf_success = 0
    failed = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\nОбрабатываю {i}/{len(pdf_files)}: {pdf_path.name}")
        
        result = parser.parse_article(pdf_path)
        
        if result:
            results.append(result)
            if result['method'] == 'GROBID':
                grobid_success += 1
                print(f"✓ GROBID: {result['title']}")
            else:
                pymupdf_success += 1
                print(f"✓ PyMuPDF: {result['title']}")
            
            print(f"  Абстракт: {result['abstract_length']} символов")
            print(f"  Текст: {result['text_length']} символов")
            
            article_filename = f"{result['title']}_{result['method']}.json"
            article_path = output_dir / article_filename
            
            with open(article_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
        else:
            failed += 1
            print(f"✗ Ошибка: {pdf_path.name}")
        
        time.sleep(1)  
    
    if results:
        main_result_path = output_dir / "all_articles.json"
        with open(main_result_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        #  статистический отчет
        stats = {
            "total_files": len(pdf_files),
            "successful": len(results),
            "grobid_success": grobid_success,
            "pymupdf_success": pymupdf_success,
            "failed": failed,
            "success_rate": f"{len(results)/len(pdf_files)*100:.1f}%"
        }
        
        stats_path = output_dir / "parsing_statistics.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== РЕЗУЛЬТАТЫ ===")
        print(f"Всего файлов: {len(pdf_files)}")
        print(f"Успешно обработано: {len(results)}")
        print(f"  - GROBID: {grobid_success}")
        print(f"  - PyMuPDF: {pymupdf_success}")
        print(f"Ошибок: {failed}")
        print(f"Процент успеха: {len(results)/len(pdf_files)*100:.1f}%")
        
        print(f"\nРезультаты сохранены в:")
        print(f"  - Общий файл: {main_result_path}")
        print(f"  - Статистика: {stats_path}")
        print(f"  - Отдельные статьи: {output_dir}/")
    else:
        print("Не удалось обработать ни одной статьи")

if __name__ == "__main__":
    main() 