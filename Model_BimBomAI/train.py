"""Entry point tương thích đường dẫn cũ; dùng train.py ở gốc dự án."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from train import main
if __name__ == '__main__':
    main()

