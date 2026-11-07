import { test, expect } from "@playwright/test";

for(const role of ["administrator","management"] as const){
  test(`${role} cleanup preserves analytical navigation, role controls and responsive pages`,async({page},testInfo)=>{
    const user={id:"00000000-0000-4000-8000-000000000001",aud:"authenticated",role:"authenticated",email:"qa@local.invalid",app_metadata:{},user_metadata:{},created_at:"2025-01-01T00:00:00Z"};
    const encode=(v:object)=>Buffer.from(JSON.stringify(v)).toString("base64url");
    const token=`${encode({alg:"HS256",typ:"JWT"})}.${encode({sub:user.id,exp:Math.floor(Date.now()/1000)+3600,role:"authenticated"})}.isolated-test-signature`;
    await page.route("https://ocroshaikrfzvwtpbqzs.supabase.co/auth/v1/**",route=>route.fulfill({json:user}));
    await page.route(/^http:\/\/127\.0\.0\.1:(8010|8077)\//,async route=>{
      const url=new URL(route.request().url());url.port="8077";
      const response=await route.fetch({url:url.href,headers:{...route.request().headers(),"x-qa-role":role}});
      await route.fulfill({response});
    });
    await page.addInitScript(({user,token})=>localStorage.setItem("sb-ocroshaikrfzvwtpbqzs-auth-token",JSON.stringify({access_token:token,refresh_token:"isolated-test",expires_at:Math.floor(Date.now()/1000)+3600,expires_in:3600,token_type:"bearer",user})),{user,token});
    const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
    for(const route of ["rfm","settlement"]){
      await page.goto(`/analytics/${route}`);
      await expect(page.getByRole("table")).toBeVisible();
      await expect(page.locator("tbody tr")).toHaveCount(10);
      await expect(page.getByRole("button",{name:"Export",exact:true})).toHaveCount(role==="administrator"?1:0);
      await page.getByRole("button",{name:`Next ${route==="rfm"?"RFM":"settlement"} page`}).click();
      const explanation=page.getByRole("link",{name:"View Account Explanation"}).first();
      const target=await explanation.getAttribute("href");
      expect(target).toMatch(/^\/accounts\/[a-f0-9-]+\?/);
      await explanation.click();
      await expect(page.getByRole("heading",{name:"Historical RFM profile"})).toBeVisible();
      await expect(page.getByText(/RFM Mean = \(/)).toBeVisible();
      await expect(page.getByText("Current cumulative source ledger, not a snapshot of the published run")).toBeVisible();
      await page.getByRole("link",{name:route==="rfm"?"Back to RFM":"Back to Settlement",exact:true}).click();
      await expect(page.getByText("Showing 11-20 of 84")).toBeVisible();
    }
    await page.goto("/analytics/predictive");
    await expect(page.getByText("Final study prediction",{exact:true})).toBeVisible();
    await expect(page.getByText("The displayed classes are forecasts, not verified future sales outcomes.")).toBeVisible();
    for(const removed of ["Model SHA-256","Model version","Monitoring","catboost_stage8"]) await expect(page.getByText(removed,{exact:true})).toHaveCount(0);
    await page.getByRole("link",{name:/View .* study accounts: With Future Sales/}).click();
    await expect(page.getByRole("table")).toBeVisible();
    await page.goto("/settings");
    for(const removed of ["Effective analytics configuration","Future Macro F1","Artifact SHA-256","Account alias review"]) await expect(page.getByText(removed,{exact:true})).toHaveCount(0);
    if(role==="administrator"){
      await expect(page.getByRole("heading",{name:"Account Information Management"})).toBeVisible();
      await expect(page.getByText("No account information currently requires verification.")).toBeVisible();
      await page.getByRole("button",{name:"All",exact:true}).click();
      await page.getByLabel("Find an account").fill("ROSTRAM");
      await page.getByRole("button",{name:/Edit account information/}).click();
      await expect(page.getByRole("button",{name:"Save verified information"})).toBeVisible();
      await page.getByRole("button",{name:"Cancel",exact:true}).click();
      await page.goto("/import");
      await expect(page.locator(".source-field-grid details")).toHaveCount(10);
      await page.locator(".source-field-grid summary").filter({hasText:/^EWT$/}).click();
      await expect(page.getByText(/blank is not zero/)).toBeVisible();
      await page.goto("/import/history");
      await expect(page.getByRole("columnheader",{name:"Batch details"})).toBeVisible();
      await expect(page.getByRole("columnheader",{name:"Issues",exact:true})).toHaveCount(0);
      await page.getByRole("button",{name:/View import details:/}).first().click();
      await expect(page.getByRole("button",{name:"Download validation issue report"})).toBeVisible();
    }else{
      await expect(page.getByRole("heading",{name:"Account Information Management"})).toHaveCount(0);
      await page.goto("/import");
      await expect(page.getByRole("alert").getByText("Administrator access required")).toBeVisible();
    }
    await page.goto("/reports");
    for(const tab of ["Management Overview","Account & Prioritization Insights","Analytics Validation"]){await page.getByRole("tab",{name:tab,exact:true}).click();await expect(page.locator(".recharts-surface").first()).toBeVisible();}
    for(const removed of ["CatBoost chronological evaluation, 2020-2022","Historical lookback comparison","Historical later-period confirmations","Recomputed weights","Study outcome monitoring"]) await expect(page.getByText(removed,{exact:true})).toHaveCount(0);
    for(const viewport of [{width:1366,height:900},{width:768,height:1024},{width:390,height:844}]){
      await page.setViewportSize(viewport);
      for(const path of ["/analytics/rfm","/analytics/settlement","/analytics/predictive","/settings"]){
        await page.goto(path);if(role==="management"&&path==="/settings") await expect(page.getByRole("alert").getByText("Administrator access required")).toBeVisible();else await expect(page.locator("main h1")).toBeVisible();
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
      }
      await page.goto("/analytics/rfm");await expect(page.getByRole("table")).toBeVisible();await page.screenshot({path:testInfo.outputPath(`${role}-${viewport.width}.png`),fullPage:true});
    }
    expect(errors).toEqual([]);
  });
}
