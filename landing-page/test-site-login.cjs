const puppeteer = require('puppeteer');
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  try {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('LOG:', msg.text()));
    page.on('pageerror', err => console.log('ERR:', err.message));
    
    await page.goto('https://fake-news-detector-8djq.onrender.com/');
    await wait(2000);
    
    console.log('Logging in...');
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Get Started Free') || b.textContent.includes('Sign In'));
      if(btn) btn.click();
    });
    await wait(1000);
    
    await page.type('input[type="email"]', 'koushalkray2005@gmail.com');
    await page.type('input[type="password"]', 'Nityaray_20');
    await page.keyboard.press('Enter');
    
    await wait(4000); // wait for dashboard
    
    console.log('Navigating to Analytics...');
    await page.goto('https://fake-news-detector-8djq.onrender.com/analytics');
    await wait(3000);
    
    const rootHTML = await page.evaluate(() => document.querySelector('#root')?.innerHTML?.substring(0, 150));
    console.log("ANALYTICS ROOT HTML:", rootHTML);
    
    console.log('Navigating to History...');
    await page.goto('https://fake-news-detector-8djq.onrender.com/history');
    await wait(3000);
    
    const histHTML = await page.evaluate(() => document.querySelector('#root')?.innerHTML?.substring(0, 150));
    console.log("HISTORY ROOT HTML:", histHTML);
    
    await browser.close();
  } catch (e) {
    console.error("Puppeteer error:", e);
  }
})();
