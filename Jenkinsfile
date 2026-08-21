/*
 * AI 辅助接口自动化测试框架的参数化 Jenkins Pipeline。
 *
 * Jenkinsfile 只负责“选择环境 -> 准备隔离 Python 环境 -> 安装依赖 -> 调用统一 run.py -> 归档证据”。
 * ENV_FILE 只是一个可选的仓库外 YAML 路径：Pipeline 不读取其中字段、不复制文件内容，也不知道
 * 当前接入的是哪一种业务系统。新增其他真实 SUT 时继续复用同一条 Pipeline。
 */
pipeline {
    // any 允许 Jenkins 根据现有节点资源调度；真实 SUT 可以部署在 Windows 或 Linux Agent 可访问的位置。
    agent any

    // Windows Service 常运行在中文系统区域设置下，Python 可能默认使用 CP936/GBK。
    // 项目文本统一 UTF-8，因此仅在当前 Pipeline 进程树启用 Python UTF-8 Mode，不改整机全局设置。
    environment {
        PYTHONUTF8 = '1'
    }

    options {
        // 已显式定义 Checkout stage，关闭 Declarative Pipeline 的隐式 checkout，避免重复拉取。
        skipDefaultCheckout(true)
        // 同一 Job 不并发执行，避免多个构建同时操作共享测试环境而互相污染数据。
        disableConcurrentBuilds()
    }

    parameters {
        // ENV_NAME 只对应 config/env.<name>.yaml 的逻辑名称；它不是任何具体项目枚举。
        string(
            name: 'ENV_NAME',
            defaultValue: 'test',
            description: '环境配置名称，对应 config/env.<name>.yaml；新增真实项目无需修改 Jenkinsfile'
        )
        // LEVEL 是框架级稳定语义，由统一 run.py 转换成 Pytest marker 选择。
        choice(
            name: 'LEVEL',
            choices: ['smoke', 'core', 'regression', 'all'],
            description: '选择本次执行的测试层级'
        )
        // SELECTION 只把用户策略交给统一 run.py；Jenkins 不实现 Contract Diff 或 Selector。
        choice(
            name: 'SELECTION',
            choices: ['full', 'auto'],
            description: '回归选择策略；full 保持完整层级执行，auto 显式启用 Stage 6'
        )
        // Preview 只生成 selection.json/md，不启动 Pytest；仅在 AUTO 模式下有效。
        booleanParam(
            name: 'SELECTION_ONLY',
            defaultValue: false,
            description: '仅预览 AUTO 选择结果；要求 SELECTION=auto'
        )
        // ENV_FILE 只保存“外部覆盖 YAML 路径”。留空时完全沿用仓库公开配置，适合 Mock/公共环境。
        // 真实凭据仍由用户在仓库外 YAML 中编辑，不进入 Jenkinsfile、Git 历史或命令行参数值。
        string(
            name: 'ENV_FILE',
            defaultValue: '',
            description: '可选：Jenkins Agent 上的外部环境覆盖 YAML 路径；留空则只使用仓库配置'
        )
    }

    stages {
        stage('Checkout') {
            steps {
                // 仓库地址和分支继续由 Jenkins Job 的 SCM 配置决定，Pipeline 本身不写死源代码位置。
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    // 系统 Python 只负责创建当前 Workspace 的隔离 .venv，避免污染 Anaconda Base/全局环境。
                    if (isUnix()) {
                        sh 'rm -rf .venv'
                        sh 'python --version'
                        sh 'python -m venv .venv'
                        sh '.venv/bin/python -m pip install --upgrade pip'
                        sh '.venv/bin/python -m pip install -r requirements-dev.txt -c constraints.txt'
                    } else {
                        bat 'if exist .venv rmdir /s /q .venv'
                        bat 'python --version'
                        bat 'python -m venv .venv'
                        bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                        bat '.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt -c constraints.txt'
                    }
                }
            }
        }

        stage('Run API Tests') {
            steps {
                script {
                    // BUILD_NUMBER 进入 run_id，Jenkins Build、JUnit、Allure Results 与日志可以一一对应。
                    def runId = "jenkins-${env.BUILD_NUMBER}"
                    // 私有文件参数先 trim；空字符串代表“不开启外部覆盖”，保持现有公共/Mock 行为。
                    def envFile = params.ENV_FILE?.trim()

                    // 显式指定文件却不存在时立即停止，不让框架误用公开 YAML 中的占位值继续跑业务请求。
                    if (envFile && !fileExists(envFile)) {
                        error("ENV_FILE does not exist on Jenkins Agent: ${envFile}")
                    }

                    // Preview 是用户显式控制；full + selection-only 属于无意义组合，提前给出清楚错误。
                    if (params.SELECTION_ONLY && params.SELECTION != 'auto') {
                        error('SELECTION_ONLY requires SELECTION=auto')
                    }

                    // CI 只把 Stage 6 参数交给 run.py，不在 Jenkinsfile 中复制 Diff/Dependency/Selector 逻辑。
                    def selectionArgs = "--selection \"${params.SELECTION}\""
                    if (params.SELECTION_ONLY) {
                        selectionArgs += ' --selection-only'
                    }

                    // 运行命令只包含逻辑环境、层级、选择策略和 run-id；真实 YAML 内容从不拼入 Console Output。
                    def runCommand = {
                        if (isUnix()) {
                            sh ".venv/bin/python run.py --env \"${params.ENV_NAME}\" --level \"${params.LEVEL}\" ${selectionArgs} --run-id \"${runId}\""
                        } else {
                            bat ".venv\\Scripts\\python.exe run.py --env \"${params.ENV_NAME}\" --level \"${params.LEVEL}\" ${selectionArgs} --run-id \"${runId}\""
                        }
                    }

                    if (envFile) {
                        // 仅把“路径”临时注入本次测试进程树；ConfigManager 负责读取/合并 YAML。
                        // 不 copy 到 Workspace，也不会被 reports/logs 的 Artifact 规则归档。
                        withEnv(["API_TEST_ENV_FILE=${envFile}"]) {
                            runCommand()
                        }
                    } else {
                        runCommand()
                    }
                }
            }
        }
    }

    post {
        always {
            // run.py 在 Jenkins 中把当前 BUILD_NUMBER 固化为 jenkins-<build> 运行目录。
            // 必须只读取“当前 Build”的 JUnit；Jenkins Workspace 会跨构建保留文件，若使用
            // 递归扫描整个 reports/runs 目录，会把上一轮失败结果再次读入并把本次全通过构建误标为 UNSTABLE。
            junit(
                testResults: "reports/runs/jenkins-${env.BUILD_NUMBER}/junit.xml",
                allowEmptyResults: true
            )

            // Artifacts 同样只收集当前 Build 的 reports；旧 Build 的报告由 Jenkins 自己的历史构建归档保存。
            // logs/ 继续作为框架运行日志归档，但任何仓库外 ENV_FILE 都不在 Workspace，因此不会被带入 Artifact。
            archiveArtifacts(
                artifacts: "reports/runs/jenkins-${env.BUILD_NUMBER}/**, logs/**/*",
                allowEmptyArchive: true,
                fingerprint: false
            )
        }
    }
}
