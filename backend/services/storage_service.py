"""
Servicio de almacenamiento de archivos.
Abstrae el almacenamiento usando Cloudinary para cloud deployment.
"""
import os
from typing import BinaryIO, Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import UploadFile
import logging

from backend.core.config import settings


logger = logging.getLogger(__name__)


class StorageService:
    """
    Servicio para manejar el almacenamiento de PDFs.
    Usa Cloudinary en producción o filesystem en desarrollo.
    """
    
    def __init__(self):
        """Inicializar servicio y configurar Cloudinary"""
        self.use_cloudinary = bool(settings.cloudinary_cloud_name)
        
        if self.use_cloudinary:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True
            )
            logger.info("StorageService initialized with Cloudinary")
        else:
            # Usar almacenamiento local en desarrollo
            self.local_storage_path = os.path.join(os.getcwd(), "data", "pdfs")
            os.makedirs(self.local_storage_path, exist_ok=True)
            logger.info(f"StorageService initialized with local storage: {self.local_storage_path}")
    
    async def save_pdf(
        self,
        file: UploadFile,
        empresa_id: int,
        factura_id: int
    ) -> str:
        """
        Guardar PDF en el almacenamiento.
        
        Args:
            file: Archivo PDF subido
            empresa_id: ID de la empresa (para organizar folders)
            factura_id: ID de la factura
            
        Returns:
            URL pública del archivo almacenado
        """
        try:
            if self.use_cloudinary:
                # Subir a Cloudinary
                result = cloudinary.uploader.upload(
                    file.file,
                    folder=f"facturas/{empresa_id}",
                    public_id=f"{factura_id}_{file.filename}",
                    resource_type="raw",  # Para PDFs
                    overwrite=True
                )
                logger.info(f"PDF uploaded to Cloudinary: {result['secure_url']}")
                return result["secure_url"]
            else:
                # Guardar localmente
                empresa_dir = os.path.join(self.local_storage_path, str(empresa_id))
                os.makedirs(empresa_dir, exist_ok=True)
                
                file_path = os.path.join(empresa_dir, f"{factura_id}_{file.filename}")
                
                # Guardar archivo
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # Retornar path relativo como URL
                relative_url = f"/data/pdfs/{empresa_id}/{factura_id}_{file.filename}"
                logger.info(f"PDF saved locally: {file_path}")
                return relative_url
                
        except Exception as e:
            logger.error(f"Error saving PDF: {e}")
            raise
    
    async def get_pdf(self, pdf_url: str) -> Optional[bytes]:
        """
        Obtener contenido de un PDF desde storage.
        
        Args:
            pdf_url: URL o path del PDF
            
        Returns:
            Contenido binario del PDF o None si no existe
        """
        try:
            if self.use_cloudinary:
                # Descargar de Cloudinary
                import requests
                response = requests.get(pdf_url)
                response.raise_for_status()
                return response.content
            else:
                # Leer desde filesystem local
                # Convertir URL relativa a path absoluto
                if pdf_url.startswith("/data/pdfs/"):
                    file_path = os.path.join(
                        os.getcwd(),
                        pdf_url.lstrip("/")
                    )
                else:
                    file_path = pdf_url
                
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        return f.read()
                else:
                    logger.warning(f"PDF not found: {file_path}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting PDF: {e}")
            return None
    
    async def delete_pdf(self, pdf_url: str) -> bool:
        """
        Eliminar un PDF del almacenamiento.
        
        Args:
            pdf_url: URL o path del PDF
            
        Returns:
            True si se eliminó correctamente, False si hubo error
        """
        try:
            if self.use_cloudinary:
                # Extraer public_id de la URL
                # URL format: https://res.cloudinary.com/{cloud_name}/raw/upload/v{version}/{public_id}
                parts = pdf_url.split("/")
                public_id = "/".join(parts[7:])  # Obtener public_id con folder
                public_id = public_id.split(".")[0]  # Remover extensión
                
                result = cloudinary.uploader.destroy(public_id, resource_type="raw")
                logger.info(f"PDF deleted from Cloudinary: {public_id}")
                return result.get("result") == "ok"
            else:
                # Eliminar desde filesystem local
                if pdf_url.startswith("/data/pdfs/"):
                    file_path = os.path.join(
                        os.getcwd(),
                        pdf_url.lstrip("/")
                    )
                else:
                    file_path = pdf_url
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"PDF deleted locally: {file_path}")
                    return True
                else:
                    logger.warning(f"PDF not found for deletion: {file_path}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting PDF: {e}")
            return False


# Singleton instance
storage_service = StorageService()
