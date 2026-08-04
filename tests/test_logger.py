# -- coding: utf-8 --
"""StructuredLogger 单元测试。"""

from ocrx.logger import StructuredLogger


def make_logger(tmp_path, name="ocrx_test.log"):
    return StructuredLogger(str(tmp_path / name))


def test_log_entries_and_levels(tmp_path):
    logger = make_logger(tmp_path)
    logger.debug("调试信息")
    logger.info("普通信息", "System")
    logger.warning("警告信息", "OCR")
    logger.error("错误信息", "Task")
    assert len(logger.get_logs()) == 4
    assert len(logger.get_logs(level="ERROR")) == 1
    assert logger.get_logs(level="ERROR")[0]["component"] == "Task"


def test_file_written(tmp_path):
    logger = make_logger(tmp_path)
    logger.info("写入文件的消息", "System")
    content = (tmp_path / "ocrx_test.log").read_text(encoding="utf-8")
    assert "写入文件的消息" in content


def test_export_logs(tmp_path):
    logger = make_logger(tmp_path)
    logger.info("导出内容", "System")
    out = tmp_path / "export.txt"
    assert logger.export_logs(str(out)) == str(out)
    assert "导出内容" in out.read_text(encoding="utf-8")


def test_clear_logs(tmp_path):
    logger = make_logger(tmp_path)
    logger.info("x")
    logger.clear_logs()
    assert logger.get_logs() == []


def test_gui_callback(tmp_path):
    received = []
    logger = StructuredLogger(str(tmp_path / "cb.log"), gui_callback=lambda entry: received.append(entry))
    logger.info("回调消息")
    assert len(received) == 1
    assert received[0]["message"] == "回调消息"


def test_new_instance_closes_previous_handler(tmp_path):
    """回归测试：创建新日志实例时应关闭旧文件处理器，避免文件句柄泄漏。"""
    logger1 = make_logger(tmp_path, "one.log")
    old_handler = logger1.logger.handlers[0]
    make_logger(tmp_path, "two.log")
    assert old_handler.stream is None or old_handler.stream.closed


def test_log_rotation(tmp_path):
    """日志达到上限后应轮转，而不是无限增长。"""
    logger = StructuredLogger(str(tmp_path / "rot.log"), max_bytes=500, backup_count=2)
    for i in range(20):
        logger.info(f"日志内容 {i} " + "x" * 200)
    backups = sorted(tmp_path.glob("rot.log.*"))
    assert len(backups) >= 1
    assert (tmp_path / "rot.log").exists()


def test_close_releases_handler(tmp_path):
    """回归测试：close() 后应释放文件句柄（Windows 下可正常删除日志文件）。"""
    logger = make_logger(tmp_path)
    handler = logger.logger.handlers[0]
    logger.close()
    assert logger.logger.handlers == []
    assert handler.stream is None or handler.stream.closed
    (tmp_path / "ocrx_test.log").unlink()  # 能删除说明句柄已释放
