"""
GPU描画によるプログレスバー表示

Blenderのgpuモジュールを使用して3Dビューポートに直接プログレスバーを描画します。
BlenderAddon_BakeToPSDから移植。
"""

import time

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

# GPU描画の可用性チェック
try:
    from gpu.types import GPUBatch, GPUShader
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("[WARNING] GPU module is not available")

# ========================================
# プログレスバー表示位置の設定定数
# ========================================
# 画面中央上部に大きく表示

# 基本位置・サイズ設定（動的計算用のオフセット）
DEFAULT_PROGRESS_X = -1          # -1 = 画面中央に配置（動的計算）
DEFAULT_PROGRESS_Y = 80          # 上からのオフセット
DEFAULT_PROGRESS_WIDTH = 500     # プログレスバーの幅（大きめ）
DEFAULT_PROGRESS_HEIGHT = 28     # プログレスバーの高さ（大きめ）
DEFAULT_BORDER_WIDTH = 3         # ボーダーの幅

# テキスト表示設定
TEXT_OFFSET_Y = 36              # プログレスバーからテキストまでの縦間隔
TEXT_FONT_SIZE = 16             # フォントサイズ（大きめ）
TEXT_PADDING_X = 12             # テキスト背景の横パディング
TEXT_PADDING_Y = 6              # テキスト背景の縦パディング

# 色設定（より目立つ配色）
DEFAULT_BG_COLOR = (0.15, 0.15, 0.15, 0.9)   # 背景色（濃いめ）
DEFAULT_BAR_COLOR = (0.3, 0.7, 1.0, 1.0)     # バー色（青系、エクスポート用）
DEFAULT_BORDER_COLOR = (0.4, 0.4, 0.4, 1.0)  # ボーダー色
DEFAULT_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)    # テキスト色
DEFAULT_TEXT_BG_COLOR = (0.1, 0.1, 0.1, 0.85) # テキスト背景色

# 詳細行表示設定
DETAIL_LINE_OFFSET_Y = 22       # 各行間の縦間隔
DETAIL_FONT_SIZE = 13           # 詳細行のフォントサイズ
DETAIL_TEXT_COLOR = (0.8, 0.8, 0.8, 1.0)  # 詳細行のテキスト色（やや薄め）

# デバッグ出力の制御
DEBUG_GPU_PROGRESS = False


class GPUProgressBar:
    """GPU描画によるプログレスバー"""

    def __init__(self):
        self.is_active = False
        self.percentage = 0.0
        self.message = ""
        self.draw_handler = None
        self.shader = None
        self.batch_bg = None
        self.batch_bar = None
        self.batch_text_bg = None

        # 描画設定（定数から初期化）
        self.x = DEFAULT_PROGRESS_X
        self.y = DEFAULT_PROGRESS_Y
        self.width = DEFAULT_PROGRESS_WIDTH
        self.height = DEFAULT_PROGRESS_HEIGHT
        self.border_width = DEFAULT_BORDER_WIDTH

        # 色設定（定数から初期化）
        self.bg_color = DEFAULT_BG_COLOR
        self.bar_color = DEFAULT_BAR_COLOR
        self.border_color = DEFAULT_BORDER_COLOR
        self.text_color = DEFAULT_TEXT_COLOR
        self.text_bg_color = DEFAULT_TEXT_BG_COLOR

        # 詳細情報用のインスタンス変数
        self.object_count_text = ""      # "3/10 objects"
        self.phase_name = ""             # "preprocess"
        self.current_object_name = ""    # "Cube.001"
        self.addon_detail = ""           # "AutoMerge: analyze - ..."
        self.start_time = None           # 開始時刻（経過時間計算用）

    def _init_shader(self):
        """シェーダーを初期化"""
        if not GPU_AVAILABLE:
            return False

        # 正規化座標用のシンプルなシェーダー
        vertex_shader = '''
        in vec2 pos;

        void main()
        {
            gl_Position = vec4(pos, 0.0, 1.0);
        }
        '''

        fragment_shader = '''
        uniform vec4 color;
        out vec4 fragColor;

        void main()
        {
            fragColor = color;
        }
        '''

        try:
            self.shader = gpu.types.GPUShader(vertex_shader, fragment_shader)
            return True
        except Exception as e:
            print(f"[ERROR] GPU shader creation failed: {e}")
            return False

    def _get_actual_x(self, viewport_width):
        """実際のX座標を取得（中央配置対応）"""
        if self.x < 0:
            return (viewport_width - self.width) // 2
        return self.x

    def _create_batches(self):
        """描画用バッチを作成"""
        if not self.shader:
            return

        try:
            region = bpy.context.region
            if not region:
                return

            viewport_width = region.width
            viewport_height = region.height

            if viewport_width <= 0 or viewport_height <= 0:
                return

            actual_x = self._get_actual_x(viewport_width)

            bg_vertices = self._screen_to_normalized([
                (actual_x, self.y),
                (actual_x + self.width, self.y),
                (actual_x + self.width, self.y + self.height),
                (actual_x, self.y + self.height)
            ], viewport_width, viewport_height)

            indices = [(0, 1, 2), (2, 3, 0)]

            self.batch_bg = batch_for_shader(
                self.shader, 'TRIS',
                {"pos": bg_vertices},
                indices=indices
            )

            self._update_progress_batch()

        except Exception as e:
            print(f"[ERROR] Batch creation error: {e}")
            self.batch_bg = None
            self.batch_bar = None

    def _screen_to_normalized(self, vertices, viewport_width, viewport_height):
        """スクリーン座標を正規化座標に変換"""
        if viewport_width <= 0 or viewport_height <= 0:
            return [(0.0, 0.0)] * len(vertices)

        normalized_vertices = []
        for x, y in vertices:
            norm_x = (x / viewport_width) * 2.0 - 1.0
            norm_y = -((y / viewport_height) * 2.0 - 1.0)
            normalized_vertices.append((norm_x, norm_y))
        return normalized_vertices

    def _update_progress_batch(self):
        """プログレスバーの幅を更新"""
        if not self.shader:
            return

        try:
            region = bpy.context.region
            if not region:
                return

            viewport_width = region.width
            viewport_height = region.height

            if viewport_width <= 0 or viewport_height <= 0:
                return

            actual_x = self._get_actual_x(viewport_width)

            padding = self.border_width
            inner_width = max(0, (self.width - padding * 2) * (self.percentage / 100.0))

            if inner_width <= 0:
                bar_screen_vertices = [
                    (actual_x + padding, self.y + padding),
                    (actual_x + padding, self.y + padding),
                    (actual_x + padding, self.y + self.height - padding),
                    (actual_x + padding, self.y + self.height - padding)
                ]
            else:
                bar_screen_vertices = [
                    (actual_x + padding, self.y + padding),
                    (actual_x + padding + inner_width, self.y + padding),
                    (actual_x + padding + inner_width, self.y + self.height - padding),
                    (actual_x + padding, self.y + self.height - padding)
                ]

            bar_vertices = self._screen_to_normalized(bar_screen_vertices, viewport_width, viewport_height)

            indices = [(0, 1, 2), (2, 3, 0)]

            self.batch_bar = batch_for_shader(
                self.shader, 'TRIS',
                {"pos": bar_vertices},
                indices=indices
            )

        except Exception as e:
            print(f"[ERROR] Progress batch update error: {e}")
            self.batch_bar = None

    def _draw_callback(self):
        """描画コールバック関数"""
        if not self.is_active or not GPU_AVAILABLE:
            return

        saved_blend = None
        saved_depth_test = None

        try:
            region = bpy.context.region
            if not region:
                return

            if region.width <= 0 or region.height <= 0:
                return

            if not hasattr(self, '_last_viewport_size'):
                self._last_viewport_size = (0, 0)

            current_size = (region.width, region.height)
            if current_size != self._last_viewport_size:
                self._last_viewport_size = current_size
                self._create_batches()

            if not (self.shader and self.batch_bg and self.batch_bar):
                return

            try:
                saved_blend = gpu.state.blend_get()
                saved_depth_test = gpu.state.depth_test_get()
            except (AttributeError, TypeError):
                pass

            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('NONE')

            self.shader.bind()

            self.shader.uniform_float("color", self.bg_color)
            self.batch_bg.draw(self.shader)

            if self.percentage > 0:
                self.shader.uniform_float("color", self.bar_color)
                self.batch_bar.draw(self.shader)

        except Exception as e:
            print(f"[ERROR] GPU draw error: {e}")
        finally:
            try:
                if saved_blend is not None:
                    gpu.state.blend_set(saved_blend)
                else:
                    gpu.state.blend_set('NONE')

                if saved_depth_test is not None:
                    gpu.state.depth_test_set(saved_depth_test)
                else:
                    gpu.state.depth_test_set('LESS_EQUAL')
            except Exception:
                try:
                    gpu.state.blend_set('NONE')
                    gpu.state.depth_test_set('LESS_EQUAL')
                except (AttributeError, TypeError):
                    pass

        try:
            self._draw_text()
        except Exception as e:
            print(f"[ERROR] Text draw error: {e}")

    def _draw_text(self):
        """テキストを描画（3行表示）"""
        try:
            region = bpy.context.region
            if not region:
                return

            font_id = 0
            actual_x = self._get_actual_x(region.width)

            # Line 1: メッセージ(45%) 3/10 | [phase] | obj（統合行）
            line1_y = region.height - self.y - self.height - TEXT_OFFSET_Y
            line1_parts = []

            # メッセージとパーセンテージ
            if self.message:
                line1_parts.append(f"{self.message} ({self.percentage:.0f}%)")
            else:
                line1_parts.append(f"{self.percentage:.0f}%")

            # オブジェクト数
            if self.object_count_text:
                line1_parts.append(self.object_count_text)

            # フェーズ名
            if self.phase_name:
                line1_parts.append(f"[{self.phase_name}]")

            # オブジェクト名
            if self.current_object_name:
                line1_parts.append(self.current_object_name)

            line1_text = " | ".join(line1_parts) if len(line1_parts) > 1 else line1_parts[0]

            blf.size(font_id, TEXT_FONT_SIZE)
            text_width, text_height = blf.dimensions(font_id, line1_text)
            text_x = actual_x + (self.width - text_width) / 2

            self._draw_text_background(text_x, line1_y, text_width, text_height, region)

            blf.position(font_id, text_x, line1_y, 0)
            blf.color(font_id, *self.text_color)
            blf.draw(font_id, line1_text)

            # Line 2: 連携アドオン詳細
            line2_y = line1_y - DETAIL_LINE_OFFSET_Y
            if self.addon_detail:
                blf.size(font_id, DETAIL_FONT_SIZE)
                text_width2, text_height2 = blf.dimensions(font_id, self.addon_detail)
                text_x2 = actual_x + (self.width - text_width2) / 2

                self._draw_text_background(text_x2, line2_y, text_width2, text_height2, region)

                blf.position(font_id, text_x2, line2_y, 0)
                blf.color(font_id, *DETAIL_TEXT_COLOR)
                blf.draw(font_id, self.addon_detail)

            # Line 3: 経過時間
            line3_y = line2_y - DETAIL_LINE_OFFSET_Y
            if self.start_time is not None:
                elapsed = time.perf_counter() - self.start_time
                elapsed_text = self._format_elapsed_time(elapsed)

                blf.size(font_id, DETAIL_FONT_SIZE)
                text_width3, text_height3 = blf.dimensions(font_id, elapsed_text)
                text_x3 = actual_x + (self.width - text_width3) / 2

                self._draw_text_background(text_x3, line3_y, text_width3, text_height3, region)

                blf.position(font_id, text_x3, line3_y, 0)
                blf.color(font_id, *DETAIL_TEXT_COLOR)
                blf.draw(font_id, elapsed_text)

        except Exception as e:
            if DEBUG_GPU_PROGRESS:
                print(f"[ERROR] Text draw error: {e}")

    def _draw_text_background(self, text_x, text_y, text_width, text_height, region):
        """テキスト背景ボックスを描画"""
        if not self.shader:
            return

        try:
            bg_x_screen = text_x - TEXT_PADDING_X
            bg_y_screen = region.height - text_y - text_height - TEXT_PADDING_Y
            bg_width = text_width + TEXT_PADDING_X * 2
            bg_height = text_height + TEXT_PADDING_Y * 2

            bg_screen_vertices = [
                (bg_x_screen, bg_y_screen),
                (bg_x_screen + bg_width, bg_y_screen),
                (bg_x_screen + bg_width, bg_y_screen + bg_height),
                (bg_x_screen, bg_y_screen + bg_height)
            ]

            bg_vertices = self._screen_to_normalized(bg_screen_vertices, region.width, region.height)

            indices = [(0, 1, 2), (2, 3, 0)]

            self.batch_text_bg = batch_for_shader(
                self.shader, 'TRIS',
                {"pos": bg_vertices},
                indices=indices
            )

            saved_blend = None
            saved_depth_test = None

            try:
                saved_blend = gpu.state.blend_get()
                saved_depth_test = gpu.state.depth_test_get()
            except (AttributeError, TypeError):
                pass

            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('NONE')

            self.shader.bind()
            self.shader.uniform_float("color", self.text_bg_color)
            self.batch_text_bg.draw(self.shader)

        except Exception as e:
            if DEBUG_GPU_PROGRESS:
                print(f"[ERROR] Text background draw error: {e}")
        finally:
            try:
                if saved_blend is not None:
                    gpu.state.blend_set(saved_blend)
                else:
                    gpu.state.blend_set('NONE')

                if saved_depth_test is not None:
                    gpu.state.depth_test_set(saved_depth_test)
                else:
                    gpu.state.depth_test_set('LESS_EQUAL')
            except Exception:
                try:
                    gpu.state.blend_set('NONE')
                    gpu.state.depth_test_set('LESS_EQUAL')
                except (AttributeError, TypeError):
                    pass

    def begin(self, min_value: float = 0.0, max_value: float = 100.0) -> bool:
        """プログレスバー表示を開始"""
        if not GPU_AVAILABLE:
            return False

        if self.is_active:
            return True

        try:
            if min_value < 0 or max_value <= min_value:
                return False

            if not bpy.context.region:
                return False

            if not self._init_shader():
                return False

            self._create_batches()

            if not (self.batch_bg and self.batch_bar):
                return False

            try:
                self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                    self._draw_callback,
                    (),
                    'WINDOW',
                    'POST_PIXEL'
                )
            except Exception as e:
                print(f"[ERROR] Draw handler registration failed: {e}")
                return False

            self.is_active = True
            self.percentage = min_value
            self.start_time = time.perf_counter()  # 開始時刻を記録

            self._redraw_viewport()
            return True

        except Exception as e:
            print(f"[ERROR] GPU progress bar begin error: {e}")
            try:
                self.end()
            except Exception:
                pass
            return False

    def update(
        self,
        percentage: float,
        message: str = "",
        *,
        current_index: int = 0,
        total_count: int = 0,
        phase: str = "",
        object_name: str = ""
    ):
        """プログレスバーを更新

        Args:
            percentage: 進捗率（0.0〜100.0）
            message: メインメッセージ
            current_index: 現在のオブジェクトインデックス（1始まり）
            total_count: 総オブジェクト数
            phase: 処理フェーズ名
            object_name: 現在処理中のオブジェクト名
        """
        if not self.is_active:
            return

        try:
            old_percentage = self.percentage
            self.percentage = max(0.0, min(100.0, percentage))
            self.message = message if message else ""

            # 詳細情報を更新
            if total_count > 0:
                self.object_count_text = f"{current_index}/{total_count}"
            else:
                self.object_count_text = ""

            self.phase_name = phase
            self.current_object_name = object_name

            # 連携アドオンの詳細情報を解析
            self.addon_detail = self._parse_addon_detail(phase, message)

            if abs(self.percentage - old_percentage) >= 0.1:
                self._update_progress_batch()

            self._redraw_viewport()

        except Exception as e:
            if DEBUG_GPU_PROGRESS:
                print(f"[ERROR] GPU progress bar update error: {e}")

    def end(self):
        """プログレスバー表示を終了"""
        if not self.is_active:
            return

        self.is_active = False

        if self.draw_handler:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            except Exception as e:
                print(f"[ERROR] Draw handler remove error: {e}")
            finally:
                self.draw_handler = None

        try:
            self.batch_bg = None
            self.batch_bar = None
            self.batch_text_bg = None
            self.shader = None

            # 詳細情報をクリア
            self.object_count_text = ""
            self.phase_name = ""
            self.current_object_name = ""
            self.addon_detail = ""
            self.start_time = None

            if hasattr(self, '_last_viewport_size'):
                del self._last_viewport_size

        except Exception as e:
            print(f"[WARNING] Resource cleanup error: {e}")

        self._redraw_viewport()

    def _redraw_viewport(self):
        """ビューポートの再描画をトリガー"""
        try:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except Exception as e:
            print(f"[ERROR] Viewport redraw error: {e}")

    def _parse_addon_detail(self, phase: str, message: str) -> str:
        """phaseから連携アドオンの詳細情報を解析"""
        if not phase:
            return ""

        if phase.startswith("merge_"):
            sub_phase = phase[6:]  # "merge_" を除去
            if message:
                return f"AutoMerge: {sub_phase} - {message}"
            return f"AutoMerge: {sub_phase}"
        elif phase.startswith("apply_"):
            sub_phase = phase[6:]
            if message:
                return f"ShapeKeysUtil: {sub_phase} - {message}"
            return f"ShapeKeysUtil: {sub_phase}"
        elif phase.startswith("lr_"):
            sub_phase = phase[3:]
            if message:
                return f"ShapeKeysUtil(LR): {sub_phase} - {message}"
            return f"ShapeKeysUtil(LR): {sub_phase}"
        else:
            return ""  # 連携アドオン以外は空文字

    def _format_elapsed_time(self, elapsed: float) -> str:
        """経過時間をフォーマット"""
        if elapsed < 1:
            return f"Elapsed: {elapsed * 1000:.0f} ms"
        elif elapsed < 60:
            return f"Elapsed: {elapsed:.1f} sec"
        else:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            return f"Elapsed: {minutes}m {seconds:.0f}s"


# グローバルインスタンス
_gpu_progress_bar = None


def get_gpu_progress_bar() -> GPUProgressBar:
    """グローバルGPUプログレスバーを取得"""
    global _gpu_progress_bar
    if _gpu_progress_bar is None:
        _gpu_progress_bar = GPUProgressBar()
    return _gpu_progress_bar


def gpu_progress_begin(min_value: float = 0.0, max_value: float = 100.0) -> bool:
    """GPUプログレスバー開始（便利関数）"""
    bar = get_gpu_progress_bar()
    return bar.begin(min_value, max_value)


def gpu_progress_update(
    percentage: float,
    message: str = "",
    *,
    current_index: int = 0,
    total_count: int = 0,
    phase: str = "",
    object_name: str = ""
):
    """GPUプログレスバー更新（便利関数）"""
    bar = get_gpu_progress_bar()
    bar.update(
        percentage,
        message,
        current_index=current_index,
        total_count=total_count,
        phase=phase,
        object_name=object_name
    )


def gpu_progress_end():
    """GPUプログレスバー終了（便利関数）"""
    bar = get_gpu_progress_bar()
    bar.end()


def is_gpu_progress_available() -> bool:
    """GPU描画が利用可能かチェック"""
    return GPU_AVAILABLE
