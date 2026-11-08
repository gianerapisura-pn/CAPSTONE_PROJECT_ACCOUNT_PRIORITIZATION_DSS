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
      const explanation=page.locator("tbody td:first-child a").first();
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
      await expect(page.getByText(/Collection correction/i)).toHaveCount(0);
      await page.goto("/import");
      await expect(page.locator(".source-field-grid details")).toHaveCount(10);
      await page.locator(".source-field-grid summary").filter({hasText:/^EWT$/}).click();
      await expect(page.getByText(/blank is not zero/)).toBeVisible();
      await expect(page.getByText(/Collection records require review/)).toHaveCount(0);
      const candidate=(id:string,amount:string)=>({raw_source_row_id:id,import_batch_id:"isolated-batch",source_sheet:"CSV",source_row_number:id==="row-1"?2:3,account_name:"Isolated correction evidence",si_no:"SI-1",si_date:"2026-01-01",si_amount:"100",cr_no:"CR-1",cr_date:"2026-01-10",cr_amount:amount,ewt:"0",payment_mode:"Bank",payment_status:"Fully Paid"});
      let correctionState="error";
      const review={collection_correction_review_id:"isolated-review",status:"pending",selected_raw_source_row_id:null as string|null,reason:null as string|null,candidates:[candidate("row-1","100"),candidate("row-2","90")]};
      await page.route("**/collection-corrections?status=all",route=>correctionState==="error"?route.fulfill({status:500,json:{detail:"Isolated test failure"}}):route.fulfill({json:[review]}));
      await page.route("**/collection-corrections/isolated-review/resolve",async route=>{
        expect(route.request().postDataJSON()).toEqual({selected_raw_source_row_id:"row-2",reason:"Verified isolated source receipt."});
        review.status="resolved";review.selected_raw_source_row_id="row-2";review.reason="Verified isolated source receipt.";
        await route.fulfill({json:{status:"resolved",analytics_publication_required:true}});
      });
      await page.reload();
      await expect(page.locator(".correction-status[role=alert]")).toContainText("Collection corrections could not be checked");
      correctionState="pending";
      await page.getByRole("button",{name:"Retry",exact:true}).click();
      await expect(page.getByText(/Collection records require review/)).toBeVisible();
      await page.getByRole("button",{name:"Review corrections"}).click();
      await expect(page.getByRole("button",{name:"Resolve correction"})).toBeDisabled();
      await page.getByRole("radio").nth(1).check();
      await page.getByRole("textbox",{name:"Resolution reason"}).fill("Verified isolated source receipt.");
      await page.getByRole("button",{name:"Resolve correction"}).click();
      await expect(page.getByText(/explicit analytics rerun is required/)).toBeVisible();
      await page.getByRole("button",{name:/Resolved \(1\)/}).click();
      await expect(page.getByText("Resolution reason: Verified isolated source receipt.")).toBeVisible();
      await expect(page.getByRole("radio").first()).toBeDisabled();
      await page.getByRole("button",{name:"Close correction review"}).click();
      await expect(page.getByRole("button",{name:"View correction history"})).toBeVisible();
      await page.unroute("**/collection-corrections?status=all");
      await page.unroute("**/collection-corrections/isolated-review/resolve");
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
      if(role==="administrator"){
        await page.goto("/settings");await page.getByRole("button",{name:"All",exact:true}).click();
        await page.getByLabel("Find an account").fill("ROSTRAM");await page.getByRole("button",{name:/Edit account information/}).click();
        const form=page.locator(".context-editor");await expect(form).toBeVisible();
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
        const inset=await page.locator(".context-body").evaluate(el=>parseFloat(getComputedStyle(el).paddingLeft));expect(inset).toBeGreaterThanOrEqual(16);
        await page.screenshot({path:testInfo.outputPath(`context-editor-${viewport.width}.png`),fullPage:true});
        await page.getByRole("button",{name:"Cancel",exact:true}).click();
      }
      await page.goto("/analytics/rfm");await expect(page.getByRole("table")).toBeVisible();await page.screenshot({path:testInfo.outputPath(`${role}-${viewport.width}.png`),fullPage:true});
    }
    expect(errors).toEqual([]);
  });
}


for(const role of ["administrator","management"] as const){
 test(`${role} account focus preserves source, filtered navigation and analytical boundaries`,async({page},testInfo)=>{
  const user={id:"00000000-0000-4000-8000-000000000001",aud:"authenticated",role:"authenticated",email:"qa@local.invalid",app_metadata:{},user_metadata:{},created_at:"2025-01-01T00:00:00Z"};
  const encode=(v:object)=>Buffer.from(JSON.stringify(v)).toString("base64url");
  const token=`${encode({alg:"HS256",typ:"JWT"})}.${encode({sub:user.id,exp:Math.floor(Date.now()/1000)+3600,role:"authenticated"})}.isolated-test-signature`;
  await page.route("https://ocroshaikrfzvwtpbqzs.supabase.co/auth/v1/**",route=>route.fulfill({json:user}));
  await page.route(/^http:\/\/127\.0\.0\.1:(8010|8077)\//,async route=>{
   const url=new URL(route.request().url());url.port="8077";
   const response=await route.fetch({url:url.href,headers:{...route.request().headers(),"x-qa-role":role}});await route.fulfill({response});
  });
  await page.addInitScript(({user,token})=>localStorage.setItem("sb-ocroshaikrfzvwtpbqzs-auth-token",JSON.stringify({access_token:token,refresh_token:"isolated-test",expires_at:Math.floor(Date.now()/1000)+3600,expires_in:3600,token_type:"bearer",user})),{user,token});
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  page.on("request",request=>{
   const url=new URL(request.url());
   if(url.port==="8010"&&url.pathname.startsWith("/accounts"))for(const key of ["focus","returnTo","viaList"])if(url.searchParams.has(key))errors.push(`UI metadata reached API: ${key}`);
  });
  for(const width of [1366,390]){
   await page.setViewportSize({width,height:900});
   for(const source of ["rfm","settlement"]){
    await page.goto(`/analytics/${source}?page=2`);await expect(page.getByText("Showing 11-20 of 84")).toBeVisible();
    const link=page.locator("tbody td:first-child a").first();expect(new URL((await link.getAttribute("href"))!,"http://local.test").searchParams.get("focus")).toBe(source);
    await link.click();const target=page.locator(`#account-${source}`);await expect(target).toBeFocused();
    const top=(await target.boundingBox())!.y;expect(top).toBeGreaterThanOrEqual(68);expect(top).toBeLessThan(250);
    await expect(page.getByText(/independently of RFM\/Settlement table ordering/)).toHaveCount(1);
    await expect(page.getByRole("link",{name:"View matching accounts"})).toHaveCount(0);
    await page.screenshot({path:testInfo.outputPath(`${role}-${source}-${width}.png`)});
    await page.getByRole("link",{name:"Next Account",exact:true}).click();await expect(target).toBeFocused();
    expect(new URL(page.url()).searchParams.get("focus")).toBe(source);
    await page.getByRole("link",{name:source==="rfm"?"Back to RFM":"Back to Settlement",exact:true}).click();
    await expect(page.getByText("Showing 11-20 of 84")).toBeVisible();
   }
  }
  await page.goto("/accounts?eligibility=ranked&priority_group=High&page=2");
  await expect(page.locator("tbody tr").first()).toBeVisible();
  const priorLink=page.locator(".decision-table tbody td:nth-child(2) a").first();const detailPath=(await priorLink.getAttribute("href"))!;
  await priorLink.click();await expect(page.locator("#account-priority")).toBeFocused();
  await page.getByRole("link",{name:"Back to Filtered Accounts",exact:true}).click();
  await expect(page).toHaveURL(url=>url.pathname === "/accounts");
  const back=new URL(page.url());expect(back.searchParams.get("page")).toBe("2");expect(back.searchParams.get("priority_group")).toBe("High");expect(back.searchParams.has("focus")).toBe(false);
  const direct=new URL(detailPath,"http://local.test").pathname;
  for(const suffix of ["","?focus=unsupported","?focus=rfm&focus=settlement"]){
   await page.goto(direct+suffix);await expect(page.locator("#account-priority")).toBeVisible();
   expect(await page.evaluate(()=>document.activeElement?.id)).not.toMatch(/^account-(rfm|settlement|priority)$/);
  }
  expect(errors).toEqual([]);
 });
}
