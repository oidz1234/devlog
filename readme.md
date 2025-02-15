This repo is for my devlog script webpage geneartion ting.

I update devlog.txt with stuff I've done and want made public. Basically a way
to shame me if I don't do work.

Copy this if you want but change the template a little.

## Crontab

```
# Deploy to a specific directory every hour
0 * * * * cd /path/to/script && DEVLOG_OUTPUT_DIR=/var/www/html ./generate_devlog.py
```


## Example devlog.txt Format

```text
2024-02-15
Implemented new REST API endpoints for user authentication.
- Added JWT token validation
- Created rate limiting middleware
- Set up API documentation using Swagger

Next steps: Add refresh token rotation.
#backend #api


2024-02-14
Redesigned the dashboard UI components:
* New card layout for metrics
* Improved mobile responsiveness
* Added dark mode support

Created Figma mockups for review.
#frontend #ui


2024-02-13
Set up CI/CD pipeline using GitHub Actions:
1. Automated testing
2. Docker image builds
3. Deployment to staging environment

Found and fixed issue with cached dependencies in Docker layers.
#devops #deployment
```
