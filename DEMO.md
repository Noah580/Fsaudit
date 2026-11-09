rm -rf ~/Documents/demo_fsaudit && cp -R ~/Documents/demo_fsaudit_original ~/Documents/demo_fsaudit
rm -f fsaudit.db
rm -rf ~/Documents/sauvegarde_demo
uv run fsaudit scans

uv run fsaudit scan ~/Documents/demo_fsaudit

uv run fsaudit dupes

uv run fsaudit top -n 3

uv run fsaudit ext

uv run fsaudit backup ~/Documents/sauvegarde_demo

echo "nouveau" > ~/Documents/demo_fsaudit/cours/nouveau.txt
rm ~/Documents/demo_fsaudit/brouillon.txt
echo "modif" >> ~/Documents/demo_fsaudit/projet/main.py

uv run fsaudit scan ~/Documents/demo_fsaudit

uv run fsaudit scans

uv run fsaudit backup ~/Documents/sauvegarde_demo

uv run fsaudit top --scan 99
uv run fsaudit top -n -1

uv run pytest
