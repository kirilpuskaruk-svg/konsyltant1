@echo off
echo =========================================
echo 🚀 Deploying latest code to GitHub & Vercel
echo =========================================
git add -A
git commit -m "Auto update and deploy"
git push origin main
npx vercel --cwd webapp --yes --prod --force
echo =========================================
echo ✅ Deployment Complete!
echo =========================================
pause
