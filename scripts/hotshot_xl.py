import install

import os
import gradio as gr
from modules import script_callbacks, scripts, shared
from modules.processing import (Processed, StableDiffusionProcessing,
                                StableDiffusionProcessingImg2Img)
from typing import Any, Union, Dict

try:
    from scripts.hotshot_xl_ui import HotshotXLUiGroup, HotshotXLParams
    from scripts.hotshot_xl_model_controller import model_controller
    from scripts.hotshot_xl_output import HotshotXLOutput
except:
    ...

script_dir = scripts.basedir()

class HotshotXLScript(scripts.Script):

    def __init__(self):
        print("HotshotXLScript init")
        self.lora_hacker = None
        self.cfg_hacker = None
        self.cn_hacker = None
        os.makedirs(self.model_directory, exist_ok=True)

    @property
    def model_directory(self):
        return shared.opts.data.get("hotshot_xl_model_path", os.path.join(script_dir, "model"))

    def title(self):
        return "Hotshot-XL"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return (HotshotXLUiGroup().render(is_img2img, self.model_directory),)

    def before_process(
            self, p: StableDiffusionProcessing, params: Union[Dict, HotshotXLParams]
    ):
        if shared.sd_model and not shared.sd_model.is_sdxl:
            print("disabling because sdxl is not loaded...")
            return

        if isinstance(params, dict): params = HotshotXLParams(**params)
        if params is not None and params.enable:
            params.set_p(p)

            # we don't cache the conditioning because we modify it using
            # original width and height & target width and height
            # which aren't part of the cache key

            p.cached_c = [None, None]
            p.cached_uc = [None, None]

            model_path = os.path.join(self.model_directory, params.model)
            model_controller.load_and_inject(
                shared.sd_model,
                model_path,
                cond={
                    "positive": {
                        "og_size": (params.original_size_width, params.original_size_height),
                        "tgt_size": (params.target_size_width, params.target_size_width),
                    },
                    "negative": {
                        "og_size": (params.negative_original_size_width, params.negative_original_size_height),
                        "tgt_size": (params.negative_target_size_width, params.negative_target_size_width),
                    }
                }
            )
            model_controller.set_video_length(params.video_length)

    def before_process_batch(
            self, p: StableDiffusionProcessing, params: Union[Dict, HotshotXLParams], **kwargs
    ):
        if isinstance(params, dict): params = HotshotXLParams(**params)
        if params is not None and params.enable and isinstance(p, StableDiffusionProcessingImg2Img):
            # - not supported
            ...

    def postprocess(
            self, p: StableDiffusionProcessing, res: Processed, params: Union[Dict, HotshotXLParams]
    ):
        if isinstance(params, dict): params = HotshotXLParams(**params)
        if params is not None and params.enable:
            model_controller.restore(shared.sd_model)
            HotshotXLOutput().output(p, res, params)


def on_ui_settings():
    section = ("hotshotxl", "Hotshot-XL")
    pass

def on_model_load(model):
    print("model loaded. ")

script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_after_component(HotshotXLUiGroup.on_after_component)
script_callbacks.on_model_loaded(on_model_load)

