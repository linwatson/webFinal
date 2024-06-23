@echo on
python -m venv env

call env\Scripts\activate

pip install -r requirements.txt

python createDB.py
