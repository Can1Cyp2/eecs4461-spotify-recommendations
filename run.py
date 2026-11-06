# runs the three listening scenarios at all five weights: python run.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from project_model.experiment import main

if __name__ == "__main__":
    main()

