const db = require('./config/database');

async function test() {
    await db.initialize();
    const pool = db.getPool();
    const conn = await pool.getConnection();

    const r = await conn.execute('SELECT * FROM GDWUUKT.ORDER_DT WHERE ROWNUM=1');
    console.log('ORDER_DT 欄位:', r.metaData.map(m => m.name));

    await conn.close();
    await db.close();
}

test();
