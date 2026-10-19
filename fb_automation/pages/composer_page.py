"""Composer page (publish a post with optional media)."""
from __future__ import annotations

import logging
import platform
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from fb_automation import config
from fb_automation.locators.contract import COMPOSER_PAGE
from fb_automation.utils import url_parse
from .base_page import BasePage

logger = logging.getLogger(__name__)


class ComposerPage(BasePage):
    SELECTORS = COMPOSER_PAGE

    def post(self, url: str, message: str = "", media_path: str = "") -> bool:
        parsed = url_parse(url)
        if parsed is None:
            return False

        logger.info("=== INICIANDO POST [NUEVO FLUJO] ===")
        try:
            logger.info("[1/5] Navegando a %s", parsed)
            self.goto(parsed)

            if message or media_path:
                logger.info("[2/5] Abriendo modal...")
                try:
                    self.click("open_editor", timeout=5)
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@role="dialog"]'))
                    )
                except Exception as e:
                    logger.warning("No se abrió el modal (¿mbasic?): %s", e)

            if media_path:
                logger.info("[3/5] Adjuntando media...")
                media_path = self._normalize_media_path(media_path)

                # Buscamos el input de archivo ESPECÍFICAMENTE dentro del diálogo
                # Si no está en el diálogo, usamos el último de la página.
                file_input = None
                try:
                    file_input = self.driver.find_element(By.XPATH, '//div[@role="dialog"]//input[@type="file"]')
                except Exception:
                    inputs = self.driver.find_elements(By.XPATH, '//input[@type="file"]')
                    if inputs:
                        file_input = inputs[-1] # El último suele ser el del modal

                if not file_input:
                    logger.error("No se encontró ningún input de archivo.")
                    return False

                # Hacemos visible el input para que Selenium pueda escribir en él
                logger.info("Forzando visibilidad del input...")
                self.driver.execute_script(
                    "arguments[0].style.display = 'block'; "
                    "arguments[0].style.visibility = 'visible'; "
                    "arguments[0].style.opacity = '1';",
                    file_input
                )

                logger.info("Inyectando archivo: %s", media_path)
                file_input.send_keys(media_path)

                logger.info("Esperando a que aparezca el botón de 'Editar' o el video...")
                # Buscamos botones que SOLO aparecen cuando el archivo ya se subió
                WebDriverWait(self.driver, 120).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        '//div[@role="dialog"]//video | '
                        '//div[@role="dialog"]//*[@aria-label="Quitar" or @aria-label="Remove" or @aria-label="Editar" or @aria-label="Edit"]'
                    ))
                )
                logger.info("¡Media subida y detectada con éxito!")
                time.sleep(2)

            if message:
                logger.info("[4/5] Escribiendo texto...")
                try:
                    self.click("message", timeout=5)
                except Exception:
                    pass

                # Type_text tiene su propia validación que lanza error si falla
                self.type_text("message", message, timeout=config.POST_TIMEOUT)
                logger.info("Texto inyectado.")

                # Clic en el título para quitar el foco del hashtag (en vez de ESCAPE)
                try:
                    self.driver.find_element(By.XPATH, '//div[@role="dialog"]//h2 | //*[text()="Crear publicación"]').click()
                    time.sleep(1)
                except Exception:
                    pass

            logger.info("[5/5] Verificando botón Publicar...")
            submit_btn = self.find("submit", timeout=10)
            WebDriverWait(self.driver, 10).until(
                lambda d: submit_btn.get_attribute("aria-disabled") != "true"
            )

            logger.info("Haciendo clic en Publicar...")
            submit_btn.click()
            logger.info("=== POST FINALIZADO CON ÉXITO ===")
            return True

        except Exception as e:
            logger.error("=== FALLÓ EL POST: %s ===", e)
            return False

    @staticmethod
    def _normalize_media_path(media_path: str) -> str:
        if platform.system() == "Windows":
            return media_path.replace("/", "\\")
        return media_path