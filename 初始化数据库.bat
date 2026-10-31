@echo off
wslc run -d --rm --name mariadb -p 3306:3306 -e MARIADB_ROOT_PASSWORD=1234 -e MARIADB_DATABASE=app -e MARIADB_USER=app -e MARIADB_PASSWORD=1234 -v "%~dp0mariadb-data:/var/lib/mysql" mariadb:latest
wslc run -d --rm --name redis -p 6379:6379 -v "%~dp0redis-data:/data" redis:alpine redis-server --requirepass 1234
ping 127.0.0.1 -n 9 >nul
%~dp0tools\main.exe
pause