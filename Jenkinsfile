/*
 * AI 辅助接口自动化测试框架的参数化 Jenkins Pipeline。
 *
 * Jenkinsfile 只负责“选择环境 -> 安装依赖 -> 调用统一 run.py -> 归档证据”，
 * 不知道当前接入的是短链接、订单还是其他 SUT。只要目标 Jenkins Agent 能访问对应环境，
 * 就可以通过 ENV_NAME 切换，无需修改 Pipeline 本身。
 */
pipeline {
    // any 允许 Jenkins 根据现有节点资源调度；实际真实 SUT 可以部署在 Windows 或 Linux Agent。
    agent any

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
                    // Windows 本地真实 SUT 常用 bat；Linux Agent 则使用 sh，保持同一 Jenkinsfile 可复用。
                    if (isUnix()) {
                        sh 'python -m pip install -r requirements-dev.txt -c constraints.txt'
                    } else {
                        bat 'python -m pip install -r requirements-dev.txt -c constraints.txt'
                    }
                }
            }
        }

        stage('Run API Tests') {
            steps {
                script {
                    // run_id 使用 Jenkins BUILD_NUMBER，后续 JUnit/Allure/run.json 能直接对应某次构建。
                    def runId = "jenkins-${env.BUILD_NUMBER}"
                    // CI 只消费统一 Runner；环境选择、suite collection、marker 和报告目录仍由框架自己管理。
                    def command = "python run.py --env \"${params.ENV_NAME}\" --level \"${params.LEVEL}\" --run-id \"${runId}\""
                    if (isUnix()) {
                        sh command
                    } else {
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
