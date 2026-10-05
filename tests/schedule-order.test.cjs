const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('fs');const vm=require('vm');
const context={document:{addEventListener(){}},Intl,Date};vm.createContext(context);vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../script.js'),'utf8'),context);
test('calendar order uses full dates, not January-first DOM order',()=>{
 const groups=[{name:'jan',items:[{date:'2027-01-02'}]},{name:'oct',items:[{date:'2026-10-06'}]},{name:'dec',items:[{date:'2026-12-03'}]}];
 groups.sort((a,b)=>context.firstUpcomingDate(a.items,'2026-10-05').localeCompare(context.firstUpcomingDate(b.items,'2026-10-05')));
 assert.deepEqual(groups.map(g=>g.name),['oct','dec','jan']);
 assert.equal(context.firstUpcomingDate(groups[0].items,'2026-12-31'),'9999-12-31');
 assert.equal(context.firstUpcomingDate([{date:'2026-12-31',endDate:'2027-01-02'}],'2027-01-01'),'2026-12-31');
});
