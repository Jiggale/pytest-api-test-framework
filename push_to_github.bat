@echo off
REM ============================================================
REM  首次推送到 GitHub 的一键脚本（在 pytestDemo-mine 目录下运行）
REM  使用前请先修改下面 3 个占位符：
REM    1. YOUR_GITHUB_USERNAME  -> 你的 GitHub 用户名
REM    2. YOUR_EMAIL            -> 你的邮箱（用于 git 提交身份）
REM    3. 推送时输入的密码，请使用 GitHub 个人访问令牌(PAT)，
REM       不是你的登录密码！PAT 在 GitHub -> Settings -> Developer settings
REM       -> Personal access tokens 生成，需勾选 repo 权限。
REM ============================================================

set USERNAME=YOUR_GITHUB_USERNAME
set EMAIL=YOUR_EMAIL
set REPO=pytest-api-test-framework

REM 1. 配置 git 身份（只需一次，全局生效）
git config --global user.name "%USERNAME%"
git config --global user.email "%EMAIL%"

REM 2. 初始化仓库（副本此前已删 .git，这里是全新初始化）
git init
git branch -M main

REM 3. 添加并提交（.gitignore 已排除 report/log/__pycache__ 等）
git add .
git commit -m "接口自动化框架：分层架构+数据驱动+Allure+离线mock+CI"

REM 4. 关联远程仓库并推送
git remote add origin https://github.com/%USERNAME%/%REPO%.git
git push -u origin main

echo.
echo 推送完成。之后 GitHub 仓库的 Actions 标签页会自动运行 CI，
echo Allure 报告会发布到 https://%USERNAME%.github.io/%REPO%/
pause
