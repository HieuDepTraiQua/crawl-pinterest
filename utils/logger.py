import logging
import os
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    """Cấu hình và trả về logger cho module
    
    Args:
        name (str): Tên của module
        
    Returns:
        logging.Logger: Logger đã được cấu hình
    """
    # Tạo thư mục logs nếu chưa tồn tại
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Tạo tên file log dựa trên ngày
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{current_date}.log")
    
    # Cấu hình logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Tạo formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Thêm handler cho file
    # file_handler = logging.FileHandler(log_file, encoding='utf-8')
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)
    
    # Thêm handler cho console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger 