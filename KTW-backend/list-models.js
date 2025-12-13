import dotenv from 'dotenv';
import { GoogleGenerativeAI } from '@google/generative-ai';

dotenv.config({ path: '.env' });

const genai = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

async function listModels() {
    try {
        const models = await genai.listModels();
        console.log('可用的模型：\n');
        for (const model of models) {
            console.log(`- ${model.name}`);
            console.log(`  支援方法: ${model.supportedGenerationMethods.join(', ')}\n`);
        }
    } catch (error) {
        console.error('錯誤:', error.message);
    }
}

listModels();
