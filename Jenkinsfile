/*
 * AI 辅助接口自动化测试框架的参数化 Jenkins Pipeline。
 *
 * Jenkinsfile 只负责“选择环境 -> 准备隔离 Python 环境 -> 安装依赖 -> 调用统一 run.py -> 归档证据”，
 * 不知道当前接入的是短链接、订单还是其他 SUT。只要目标 Jenkins Agent 能访问对应环境，
 * 就可以通过 ENV_NAME 切换，无需修改 Pipeline 本身。
 */
pipeline {
    // any 允许 Jenkins 根据现有节点资源调度；实际真实 SUT 可以部署在 Windows 或 Linux Agent。
    agent any

    // Jenkins Windows Service 常运行在中文系统区域设置下，Python 可能默认使用 CP936/GBK。
    // 项目依赖文件统一保存为 UTF-8，因此仅在本 Pipeline 进程树中启用 Python UTF-8 Mode，
    // 避免修改整台 Windows 的全局编码设置，也不会影响开发者自己的其他 Python 程序。
    environment {
        PYTHONUTF8 = '1'
    }

    // 关闭同一 Job 的并发执行，避免多个回归同时操作共享测试环境而互相污染测试数据。
    options {
        // 已显式定义 Checkout stage，因此关闭 Declarative Pipeline 的隐式默认 checkout，避免重复拉取。
        skipDefaultCheckout(true)
        // 同一 Job 不并发执行，避免共享测试环境发生数据互相污染。
        disableConcurrentBuilds()
    }

    parameters {
        // 环境名直接对应 config/env.<name>.yaml；使用自由字符串才能在新增项目时保持 Jenkinsfile 不变。
        string(
            name: 'ENV_NAME',
            defaultValue: 'test',
            description: '环境配置名称，对应 config/env.<name>.yaml，例如 test 或其他真实项目环境'
        )
        // 层级是框架级稳定语义，可以安全作为固定 choice，而不包含任何具体业务模块名称。
        choice(
            name: 'LEVEL',
            choices: ['smoke', 'core', 'regression'],
            description: '选择本次执行的测试层级'
        )
    }

    stages {
        stage('Checkout') {
            steps {
                // 从 Jenkins Job 配置的 SCM 获取当前项目；Pipeline 不写死仓库地址或分支。
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    // Jenkins Service 当前能找到哪个系统 Python，只把它当作“创建隔离虚拟环境”的引导解释器。
                    // 这样不会把 pytest/requests 等测试依赖直接安装进机器上的 Anaconda Base 或其他全局环境。
                    if (isUnix()) {
                        // 每次构建重新创建 .venv，避免上一次构建残留的包版本影响本次结果。
                        sh 'rm -rf .venv'
                        sh 'python --version'
                        sh 'python -m venv .venv'
                        // 后续所有 pip 命令都使用 Workspace 内的虚拟环境解释器，确保安装和运行使用同一 Python。
                        sh '.venv/bin/python -m pip install --upgrade pip'
                        sh '.venv/bin/python -m pip install -r requirements-dev.txt -c constraints.txt'
                    } else {
                        // Windows Jenkins Agent 使用 bat；先删除旧虚拟环境，再从当前可用 Python 创建全新的 .venv。
                        bat 'if exist .venv rmdir /s /q .venv'
                        bat 'python --version'
                        bat 'python -m venv .venv'
                        // PYTHONUTF8=1 由 Pipeline environment 注入，因此 pip 读取 UTF-8 requirements 时不再回退到 CP936。
                        bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                        bat '.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt -c constraints.txt'
                    }
                }
            }
        }

        stage('Run API Tests') {
            steps {
                script {
                    // run_id 使用 Jenkins BUILD_NUMBER，后续 JUnit/Allure/run.json 能直接对应某次构建。
                    def runId = "jenkins-${env.BUILD_NUMBER}"
                    // 测试必须继续复用统一 run.py；唯一变化是使用本次构建自己的 .venv Python，
                    // 从而保证“安装依赖的解释器”和“执行测试的解释器”完全一致。
                    if (isUnix()) {
                        def command = ".venv/bin/python run.py --env \"${params.ENV_NAME}\" --level \"${params.LEVEL}\" --run-id \"${runId}\""
                        sh command
                    } else {
                        def command = ".venv\\Scripts\\python.exe run.py --env \"${params.ENV_NAME}\" --level \"${params.LEVEL}\" --run-id \"${runId}\""
                        bat command
                    }
                }
            }
        }
    }

    post {
        always {
            // JUnit 让 Jenkins 页面直接展示通过/失败数量；即使用例失败也会在 post 阶段记录结果。
            junit testResults: 'reports/runs/**/junit.xml', allowEmptyResults: true

            // 保存 Allure Results、run.json、JUnit 以及框架日志；无需强制安装 Jenkins Allure 插件。
            archiveArtifacts(
                artifacts: 'reports/runs/**/*, logs/**/*',
                allowEmptyArchive: true,
                fingerprint: false
            )
        }
    }
}
