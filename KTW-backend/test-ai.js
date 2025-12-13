import dotenv from 'dotenv';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenerativeAI } from '@google/generative-ai';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 載入 .env
dotenv.config({ path: join(__dirname, '.env') });

console.log('API Key exists:', !!process.env.GOOGLE_API_KEY);
console.log('API Key length:', process.env.GOOGLE_API_KEY?.length || 0);
console.log('API Key prefix:', process.env.GOOGLE_API_KEY?.substring(0, 10) + '...');

// 測試 Gemini
const genai = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY || '');
const model = genai.getGenerativeModel({ model: 'gemini-2.5-flash' });

try {
    const result = await model.generateContent('測試：回傳"OK"');
    console.log('\n✅ Gemini AI 連線成功!');
    console.log('回應:', result.response.text());
} catch (error) {
    console.error('\n❌ Gemini AI 連線失敗:');
    console.error(error.message);
}
