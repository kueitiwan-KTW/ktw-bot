module.exports = {
    apps: [
        {
            name: "DT-Backend",
            script: "./src/index.js",
            cwd: "./KTW-backend",
            watch: true,
            env: {
                NODE_ENV: "production",
                PORT: 3000,
                PMS_API_URL: "http://192.168.8.3:3005/api",
                // PMS-API is running on remote server (192.168.8.3)
            }
        },
        /* PMS-API removed: Running on remote server
        {
            name: "PMS-API",
            script: "./server.js",
            cwd: "./pms-api",
            watch: true,
            env: {
                PORT: 3005
            }
        },
        */
        {
            name: "DT-Admin-Web",
            script: "npm",
            args: "run dev",
            cwd: "./KTW-admin-web",
            env: {
                PORT: 5002
            }
        },
        {
            name: "Line-Bot-Py",
            script: "./run_dev.sh",
            cwd: "./",
            interpreter: "/bin/bash",
            watch: false
        },
        {
            name: "Ngrok-Tunnel",
            script: "./ngrok",
            args: "http 5001",
            cwd: "./",
            watch: false
        }
    ]
};
