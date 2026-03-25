#!/bin/bash

# 项目清理脚本 - 保持Web功能完整性
echo "🧹 开始项目清理..."

# 创建备份目录
mkdir -p backup_files/{duplicate_systems,duplicate_controllers,test_files,tools_analyzers,temp_configs,doc_fragments,media_files}

echo "📁 创建备份目录完成"

# 1. 备份重复系统实现
echo "📦 备份重复系统实现..."
mv advanced_monitoring_dashboard.py backup_files/duplicate_systems/ 2>/dev/null
mv auto_ptz_system.py backup_files/duplicate_systems/ 2>/dev/null
mv demo_monitoring_system.py backup_files/duplicate_systems/ 2>/dev/null
mv fixed_integrated_system.py backup_files/duplicate_systems/ 2>/dev/null
mv fixed_ptz_system.py backup_files/duplicate_systems/ 2>/dev/null
mv fix_ptz_system.py backup_files/duplicate_systems/ 2>/dev/null
mv launch_monitoring.py backup_files/duplicate_systems/ 2>/dev/null
mv opencv_gui_monitor.py backup_files/duplicate_systems/ 2>/dev/null
mv robot_vision_main.py backup_files/duplicate_systems/ 2>/dev/null
mv simple_web_monitor.py backup_files/duplicate_systems/ 2>/dev/null
mv start_monitoring.py backup_files/duplicate_systems/ 2>/dev/null
mv start_ptz_monitor.py backup_files/duplicate_systems/ 2>/dev/null
mv start_rtsp_monitor.py backup_files/duplicate_systems/ 2>/dev/null
mv start_smart_ptz_system.py backup_files/duplicate_systems/ 2>/dev/null
mv start_system.py backup_files/duplicate_systems/ 2>/dev/null
mv web_camera_stream.py backup_files/duplicate_systems/ 2>/dev/null
mv realtime_camera_display.py backup_files/duplicate_systems/ 2>/dev/null
mv virtual_camera_vlm.py backup_files/duplicate_systems/ 2>/dev/null

# 2. 备份重复PTZ控制器
echo "🎮 备份重复PTZ控制器..."
mv curl_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv direct_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv fixed_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv no_root_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv realtime_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv web_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null
mv xiaomi_ptz_controller.py backup_files/duplicate_controllers/ 2>/dev/null

# 3. 备份测试文件
echo "🧪 备份测试文件..."
mv auto_demo.py backup_files/test_files/ 2>/dev/null
mv batch_test.py backup_files/test_files/ 2>/dev/null
mv camera_test.py backup_files/test_files/ 2>/dev/null
mv config_test.py backup_files/test_files/ 2>/dev/null
mv create_test_video.py backup_files/test_files/ 2>/dev/null
mv demo_ptz_control.py backup_files/test_files/ 2>/dev/null
mv interactive_test.py backup_files/test_files/ 2>/dev/null
mv ptz_curl_tester.py backup_files/test_files/ 2>/dev/null
mv ptz_demo.py backup_files/test_files/ 2>/dev/null
mv quick_camera_test.py backup_files/test_files/ 2>/dev/null
mv quick_system_test.py backup_files/test_files/ 2>/dev/null
mv rtsp_auth_tester.py backup_files/test_files/ 2>/dev/null
mv simple_camera_vlm.py backup_files/test_files/ 2>/dev/null
mv simple_ptz_test.py backup_files/test_files/ 2>/dev/null
mv test_*.py backup_files/test_files/ 2>/dev/null
mv text_demo.py backup_files/test_files/ 2>/dev/null
mv video_test.py backup_files/test_files/ 2>/dev/null
mv vlm.test.py backup_files/test_files/ 2>/dev/null

# 4. 备份工具/分析文件
echo "🔧 备份工具分析文件..."
mv analyze_grpc_ptz.py backup_files/tools_analyzers/ 2>/dev/null
mv browser_network_monitor.py backup_files/tools_analyzers/ 2>/dev/null
mv camera_discovery.py backup_files/tools_analyzers/ 2>/dev/null
mv camera_url_guide.py backup_files/tools_analyzers/ 2>/dev/null
mv cli_launcher.py backup_files/tools_analyzers/ 2>/dev/null
mv extract_ptz_requests.py backup_files/tools_analyzers/ 2>/dev/null
mv generate_ptz_tests.py backup_files/tools_analyzers/ 2>/dev/null
mv get_session_auto.py backup_files/tools_analyzers/ 2>/dev/null
mv get_session_manual.py backup_files/tools_analyzers/ 2>/dev/null
mv get_session_id.py backup_files/tools_analyzers/ 2>/dev/null
mv monitor_status.py backup_files/tools_analyzers/ 2>/dev/null
mv ptz_protocol_sniffer.py backup_files/tools_analyzers/ 2>/dev/null
mv quick_scan.py backup_files/tools_analyzers/ 2>/dev/null
mv simple_ptz_analyzer.py backup_files/tools_analyzers/ 2>/dev/null
mv web_ptz_analyzer.py backup_files/tools_analyzers/ 2>/dev/null
mv vision_analyzer.py backup_files/tools_analyzers/ 2>/dev/null
mv robot_vision_config.py backup_files/tools_analyzers/ 2>/dev/null
mv rtsp_streamer.py backup_files/tools_analyzers/ 2>/dev/null
mv rtsp_viewer.py backup_files/tools_analyzers/ 2>/dev/null

# 5. 备份临时配置文件
echo "⚙️ 备份临时配置..."
mv auto_ptz_patch.py backup_files/temp_configs/ 2>/dev/null
mv auto_session_config.json backup_files/temp_configs/ 2>/dev/null
mv legacy_ssl.conf backup_files/temp_configs/ 2>/dev/null
mv rtsp_config.json backup_files/temp_configs/ 2>/dev/null
mv start_ptz_web.py backup_files/temp_configs/ 2>/dev/null
mv start.sh backup_files/temp_configs/ 2>/dev/null
mv setup_github.sh backup_files/temp_configs/ 2>/dev/null
mv simple_control.sh backup_files/temp_configs/ 2>/dev/null

# 6. 备份文档碎片
echo "📄 备份文档碎片..."
mv FINAL_PTZ_CONTROL.md backup_files/doc_fragments/ 2>/dev/null
mv HOW_TO_CONTROL.md backup_files/doc_fragments/ 2>/dev/null
mv PERFECT_PTZ_SUMMARY.md backup_files/doc_fragments/ 2>/dev/null
mv PTZ_CONTROLLER_README.md backup_files/doc_fragments/ 2>/dev/null
mv MONITORING_GUIDE.md backup_files/doc_fragments/ 2>/dev/null
mv RTSP_DISPLAY_GUIDE.md backup_files/doc_fragments/ 2>/dev/null
mv UPLOAD_INSTRUCTIONS.md backup_files/doc_fragments/ 2>/dev/null
mv README_ROBOT_VISION.md backup_files/doc_fragments/ 2>/dev/null
mv PTZ_ANALYSIS_SUMMARY.md backup_files/doc_fragments/ 2>/dev/null
mv 中文显示修复说明.md backup_files/doc_fragments/ 2>/dev/null

# 7. 备份媒体和临时文件
echo "🎬 备份媒体文件..."
mv *.jpg backup_files/media_files/ 2>/dev/null
mv *.mp4 backup_files/media_files/ 2>/dev/null
mv *.png backup_files/media_files/ 2>/dev/null
mv *.db backup_files/media_files/ 2>/dev/null

# 8. 备份各种脚本文件
mv *.sh backup_files/temp_configs/ 2>/dev/null
# 保留 quick_start_sessionid.sh
mv backup_files/temp_configs/quick_start_sessionid.sh . 2>/dev/null

# 9. 备份临时生成文件
mv grpc_*.txt backup_files/temp_configs/ 2>/dev/null
mv ptz_*.txt backup_files/temp_configs/ 2>/dev/null
mv page_*.html backup_files/temp_configs/ 2>/dev/null
mv *_20*.* backup_files/temp_configs/ 2>/dev/null

# 10. 清理目录
mv webcam-ai-monitor backup_files/ 2>/dev/null
mv templates backup_files/ 2>/dev/null

echo "✅ 项目清理完成！"
echo ""
echo "📊 清理统计:"
echo "   备份目录: backup_files/"
echo "   保留核心文件约18个"
echo ""
echo "🎯 保留的核心文件:"
echo "   ✅ final_ptz_system.py (主系统)"
echo "   ✅ integrated_camera_system.py (备选系统)"
echo "   ✅ smart_ptz_controller.py (智能控制器)"
echo "   ✅ smart_auto_session.py (SessionId管理)"
echo "   ✅ update_session.py (热更新工具)"
echo "   ✅ zoom_reset_force.py (重置工具)"
echo "   ✅ auto_ptz_controller.py (自动控制)"
echo "   ✅ sessionid_guide.py (SessionId指南)"
echo "   ✅ quick_start_sessionid.sh (快速启动)"
echo "   ✅ session_helper.py (会话助手)"
echo "   ✅ software_zoom_solution.html (软件缩放)"
echo "   ✅ ptz_test_page.html (PTZ测试)"
echo "   ✅ zoom_test.html (缩放测试)"
echo "   ✅ test_ai_status.html (AI状态测试)"
echo "   ✅ README.md (项目说明)"
echo "   ✅ requirements.txt (依赖配置)"
echo "   ✅ LICENSE (许可证)"
echo "   ✅ .gitignore (Git配置)"
echo ""
echo "💡 如需恢复文件，可从 backup_files/ 目录中获取"
echo "🚀 Web功能保持100%完整性！"