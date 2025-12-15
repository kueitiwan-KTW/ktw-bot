module.exports = {
    apps: [
        {
            name: "DT-Backend",
            script: "./src/index.js",
            cwd: "./KTW-backend",
            watch: true,
            env: {
                NODE_ENV: "production",
                PORT: 3000
            }
        },
        {
            name: "PMS-API",
            script: "./server.js",
            cwd: "./pms-api",
            watch: true,
            env: {
                PORT: 3005
            }
        },
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
