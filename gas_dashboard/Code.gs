function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
      .setTitle('รายงานวิเคราะห์ - PJ Copy Shop')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function getDashboardData(startDateStr, endDateStr) {
  const ss = SpreadsheetApp.openById('1AR2YDX190eTCFEvDyFkVcGM11TVZLL-R0WL1STf-2HM');
  
  function parseFilterDate(dateStr, isEnd) {
    let d = new Date();
    if (dateStr) {
      let parts = dateStr.split('-');
      if (parts.length === 3) {
        d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      }
    }
    if (isEnd) d.setHours(23, 59, 59, 999);
    else d.setHours(0, 0, 0, 0);
    return d;
  }

  let startD = parseFilterDate(startDateStr, false);
  let endD = parseFilterDate(endDateStr, true);
  
  // คำนวณจำนวนวันสำหรับหาค่าเฉลี่ย
  let timeDiff = endD.getTime() - startD.getTime();
  let daysDiff = Math.max(1, Math.ceil(timeDiff / (1000 * 3600 * 24)));

  function getSafeDate(dateVal) {
    if (!dateVal) return new Date(0);
    let dStr = String(dateVal).trim();
    let m1 = dStr.match(/(\d{4})[\-\/](\d{1,2})[\-\/](\d{1,2})/);
    if (m1) {
       let y = parseInt(m1[1]);
       if (y > 2500) y -= 543;
       return new Date(y, parseInt(m1[2]) - 1, parseInt(m1[3]));
    }
    let m2 = dStr.match(/(\d{1,2})[\-\/](\d{1,2})[\-\/](\d{4})/);
    if (m2) {
       let y = parseInt(m2[3]);
       if (y > 2500) y -= 543;
       return new Date(y, parseInt(m2[2]) - 1, parseInt(m2[1]));
    }
    let parsed = new Date(dStr);
    return isNaN(parsed.getTime()) ? new Date(0) : parsed;
  }

  function parseNum(val) {
    if (!val) return 0;
    let v = String(val).replace(/,/g, '').trim();
    return parseFloat(v) || 0;
  }

  function getFilteredSheetData(sheetName, dateColumnHeader) {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) return [];
    const data = sheet.getDataRange().getDisplayValues();
    if (data.length <= 1) return [];
    const headers = data[0];
    let dateIdx = headers.indexOf(dateColumnHeader);
    
    return data.slice(1).map(row => {
      let obj = {};
      headers.forEach((h, i) => { if(h) obj[String(h).trim()] = row[i]; });
      return obj;
    }).filter(row => {
      if (dateIdx === -1 || !row[dateColumnHeader]) return true; 
      let rDate = getSafeDate(row[dateColumnHeader]);
      return rDate >= startD && rDate <= endD;
    });
  }

  const rawSales = getFilteredSheetData('Raw_Sales', 'วัน-เวลา');
  const rawExpenses = getFilteredSheetData('Raw_Expenses', 'วันที่');
  const rawAdjustments = getFilteredSheetData('Raw_Adjustments', 'วันที่');
  const rawPurchases = getFilteredSheetData('Raw_Purchases', 'วันที่');

  function getSheetData(sheetName) {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) return [];
    const data = sheet.getDataRange().getDisplayValues();
    if (data.length <= 1) return [];
    const headers = data[0];
    return data.slice(1).map(row => {
      let obj = {};
      headers.forEach((h, i) => { if(h) obj[String(h).trim()] = row[i]; });
      return obj;
    });
  }

  const rawJobs = getSheetData('Raw_Jobs');
  const rawStock = getSheetData('Raw_Stock');

  let totalSales = 0, costOfGoods = 0, netProfit = 0;
  let consignmentSales = 0, expenses = 0, stockAdjust = 0;
  let cashIn = 0, transferIn = 0, purchases = 0, opex = 0, ownerDraw = 0, consignmentReturn = 0;
  let unpaidBills = 0, paidUnpaidBills = 0;
  
  let drinkSales = {};
  let otherSales = {};
  let productSalesQty = {}; // เก็บจำนวนชิ้นที่ขายได้ของแต่ละสินค้า เพื่อวิเคราะห์ความเร็ว

  rawSales.forEach(row => {
    let amount = parseNum(row['ยอดรวม']);
    let costPerUnit = parseNum(row['ต้นทุน/หน่วย']);
    let qty = parseNum(row['จำนวน']);
    let method = row['วิธีชำระ'] ? String(row['วิธีชำระ']).trim() : '';
    let status = row['สถานะบิล'] ? String(row['สถานะบิล']).trim() : '';
    let itemName = row['สินค้า/บริการ'] ? String(row['สินค้า/บริการ']).trim() : '';
    let type = row['ประเภท'] ? String(row['ประเภท']).trim().toLowerCase() : '';

    if (status === 'ยกเลิกบิล' || status === 'Hold' || status === 'Pending') return; 
    if (status === 'Unpaid') unpaidBills += amount;
    if (status === 'ชำระบิลค้างชำระ') paidUnpaidBills += amount;

    if (status !== 'Unpaid') {
      if (method === 'เงินสด' || method === 'Cash') cashIn += amount;
      else if (method === 'PromptPay' || method === 'Credit Card' || method.includes('โอน')) transferIn += amount;
      else if (method === 'Split') {
        cashIn += parseNum(row['เงินสด (Split)']);
        transferIn += parseNum(row['เงินโอน (Split)']);
      }
    }

    if (status !== 'ชำระบิลค้างชำระ') {
      totalSales += amount;
      
      // เก็บรวบรวมจำนวนชิ้นเพื่อไปวิเคราะห์ความเร็วการขาย (Velocity)
      if(!productSalesQty[itemName]) productSalesQty[itemName] = 0;
      productSalesQty[itemName] += qty;

      let isDrink = type.includes('brewed') || type.includes('เครื่องดื่ม') || type.includes('กาแฟ') || type.includes('น้ำ');
      
      costOfGoods += (costPerUnit * qty);
      
      if (isDrink) {
        if(!drinkSales[itemName]) drinkSales[itemName] = { qty: 0, amount: 0 };
        drinkSales[itemName].qty += qty; drinkSales[itemName].amount += amount;
      } else {
        if(!otherSales[itemName]) otherSales[itemName] = { qty: 0, amount: 0 };
        otherSales[itemName].qty += qty; otherSales[itemName].amount += amount;
      }
    }
  });

  rawExpenses.forEach(row => {
    let amt = parseNum(row['ยอดเงิน']);
    let expType = row['ประเภท'] ? String(row['ประเภท']).trim() : '';
    let desc = row['รายละเอียด'] ? String(row['รายละเอียด']).trim() : '';
    
    if (expType === 'Owner Draw' || expType.includes('ถอนใช้')) ownerDraw += amt;
    else if (expType === 'OPEX' || (!expType && !desc.includes('ซื้อสินค้า'))) {
      expenses += amt; opex += amt; 
    }
  });

  rawAdjustments.forEach(row => { stockAdjust += parseNum(row['ยอดเงินปรับปรุง']); });
  rawPurchases.forEach(row => { purchases += parseNum(row['ยอดเงิน']); });

  netProfit = totalSales - costOfGoods - expenses + stockAdjust;
  let netCash = cashIn + transferIn - purchases - opex - ownerDraw;

  // เรียงลำดับสินค้าขายดี (Sort by Qty)
  const drinkSalesArr = Object.keys(drinkSales).map(k => ({ name: k, qty: drinkSales[k].qty, amount: drinkSales[k].amount })).sort((a,b) => b.qty - a.qty);
  const otherSalesArr = Object.keys(otherSales).map(k => ({ name: k, qty: otherSales[k].qty, amount: otherSales[k].amount })).sort((a,b) => b.qty - a.qty);
  
  const pendingJobs = rawJobs.filter(r => {
    let s = String(r['สถานะงาน']).trim();
    return s !== 'Completed' && s !== 'เสร็จแล้ว' && s !== 'ส่งมอบแล้ว' && s !== 'ยกเลิก';
  });

  // ----------------------------------------------------
  // 🚀 ระบบวิเคราะห์แผนสั่งซื้อ (Purchase Planning Analytics)
  // ----------------------------------------------------
  let poList = [];
  let deadStock = [];
  let totalBudget = 0;

  rawStock.forEach(row => {
    let name = row['ชื่อสินค้า/บริการ'] ? String(row['ชื่อสินค้า/บริการ']).trim() : '';
    let category = row['หมวดหมู่'] ? String(row['หมวดหมู่']).trim() : '';
    let stock = parseNum(row['คงเหลือ']);
    let reorder = parseNum(row['จุดสั่งซื้อ']);
    let cost = parseNum(row['ต้นทุน']);
    
    // ข้ามสินค้าประเภทงานบริการ (Service) และเครื่องดื่มฝากขาย
    if (category === 'Service' || category === 'งานบริการ' || category.includes('Brewed')) return;

    let qtySold = productSalesQty[name] || 0;
    let velocity = (qtySold / daysDiff).toFixed(1); // ชิ้น/วัน

    // 1. วิเคราะห์สินค้าค้างสต๊อก (Dead Stock) - มีของแต่ขายไม่ได้เลย
    if (qtySold === 0 && stock > 0) {
      deadStock.push({ name: name, stock: stock, totalValue: stock * cost });
    }

    // 2. วิเคราะห์สินค้าเหลือน้อยและทำแผนซื้อ (Auto-PO)
    if (stock <= reorder) {
      // แนะนำซื้อเพิ่มให้ถึง 2 เท่าของจุดสั่งซื้อขั้นต่ำ หรือถ้าไม่มีจุดสั่งซื้อ แนะนำซื้อทีละ 10 ชิ้น
      let targetStock = reorder > 0 ? reorder * 2 : 10;
      let suggestQty = Math.max(1, targetStock - stock);
      let budget = suggestQty * cost;
      totalBudget += budget;

      poList.push({
        name: name,
        stock: stock,
        velocity: velocity,
        suggestQty: suggestQty,
        budget: budget
      });
    }
  });

  // เรียงลำดับรายการสั่งซื้อที่ต้องใช้งบเยอะสุดขึ้นก่อน
  poList.sort((a,b) => b.budget - a.budget);
  // เรียงลำดับค้างสต๊อกตามมูลค่าเงินที่จม
  deadStock.sort((a,b) => b.totalValue - a.totalValue);

  return {
    kpi: { cashIn, transferIn, unpaidBills, paidUnpaidBills },
    pl: { totalSales, consignmentSales, costOfGoods, expenses, stockAdjust, netProfit },
    cf: { cashIn, transferIn, purchases, opex, ownerDraw, consignmentReturn, netCash },
    drinkSales: drinkSalesArr,
    otherSales: otherSalesArr,
    jobs: pendingJobs,
    purchasePlan: { poList, deadStock, totalBudget }
  };
}
