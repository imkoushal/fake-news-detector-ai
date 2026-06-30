const puppeteer = require('puppeteer');
(async () => {
  try {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('LOG:', msg.text()));
    page.on('pageerror', err => console.log('ERR:', err.message));
    
    await page.goto('https://fake-news-detector-8djq.onrender.com/');
    await new Promise(resolve => setTimeout(resolve, 4000));
    
    // Evaluate if root is empty
    const rootHTML = await page.evaluate(() => document.querySelector('#root')?.innerHTML?.substring(0, 50));
    console.log("ROOT HTML START:", rootHTML);
    
    // Log in
    await page.evaluate(() => {
      // Simulate clicking sign in and submitting (or direct API token injection)
      localStorage.setItem('verify_token', 'fake-token-just-to-trigger-auth-redirect');
    });
    
    await page.reload();
    await new Promise(resolve => setTimeout(resolve, 4000));
    const postAuthHTML = await page.evaluate(() => document.querySelector('#root')?.innerHTML?.substring(0, 50));
    console.log("POST AUTH ROOT HTML START:", postAuthHTML);
    
    await browser.close();
  } catch (e) {
    console.error("Puppeteer error:", e);
  }
})();
