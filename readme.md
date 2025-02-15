This repo is for my devlog script webpage geneartion ting.

I update devlog.txt with stuff I've done and want made public. Basically a way
to shame me if I don't do work.

Copy this if you want but change the template a little.

## Crontab

```
# Deploy to a specific directory every hour
0 * * * * cd /path/to/script && DEVLOG_OUTPUT_DIR=/var/www/html ./generate_devlog.py
```
