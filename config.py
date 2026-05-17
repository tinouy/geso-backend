import os
import configparser
from pathlib import Path
from typing import Optional


class Config:
    def __init__(self, conf_path: str = "geso.conf"):
        self.conf_path = conf_path
        self.config = configparser.ConfigParser()
        
        # Cargar archivo geso.conf
        conf_file = Path(conf_path)
        if conf_file.exists():
            self.config.read(conf_path)
        
        # Cargar variables de entorno desde .env si existe
        env_file = Path(".env")
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv()
    
    def write_config(self, section: str, key: str, value: str):
        """Escribe un valor en el archivo geso.conf."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)
        
        # Escribir al archivo
        with open(self.conf_path, 'w') as configfile:
            self.config.write(configfile)
    
    def read_config_file(self) -> dict:
        """Lee el archivo geso.conf y retorna un diccionario con todos los valores."""
        result = {}
        for section in self.config.sections():
            result[section] = {}
            for key, value in self.config.items(section):
                result[section][key] = value
        return result
    
    def get(self, section: str, key: str, default: Optional[str] = None) -> str:
        """
        Obtiene un valor de configuración.
        Prioridad:
        1. Variable de entorno (formato SECTION_KEY o el nombre específico del archivo)
        2. Archivo geso.conf (que puede contener ${VAR} para variables de entorno)
        3. Valor por defecto
        """
        value = None
        
        # Primero: Intentar leer variable de entorno con formato SECTION_KEY
        env_key = f"{section}_{key}".upper()
        value = os.getenv(env_key)
        
        # Si no se encuentra, intentar leer del archivo geso.conf
        if not value:
            try:
                conf_value = self.config.get(section, key)
                # Si el valor contiene ${VAR}, reemplazar con variable de entorno
                if conf_value and conf_value.startswith("${") and conf_value.endswith("}"):
                    env_var = conf_value[2:-1]  # Extraer el nombre de la variable
                    value = os.getenv(env_var)
                    # Si la variable de entorno no existe, intentar con formato SECTION_KEY
                    if not value:
                        value = os.getenv(env_key)
                else:
                    # Si no es ${VAR}, usar el valor directamente del archivo
                    value = conf_value
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass
        
        # Si aún no hay valor, usar default
        return value if value is not None else default
    
    @property
    def database_url(self) -> str:
        return self.get("DATABASE", "url", "sqlite:///./geso.db")
    
    @property
    def secret_key(self) -> str:
        return self.get("SECURITY", "secret_key", "change-this-secret-key-in-production")
    
    @property
    def algorithm(self) -> str:
        return self.get("SECURITY", "algorithm", "HS256")
    
    @property
    def access_token_expire_minutes(self) -> int:
        return int(self.get("SECURITY", "access_token_expire_minutes", "30"))
    
    @property
    def club_name(self) -> str:
        return self.get("CLUB", "name", "Club")
    
    @property
    def frontend_url(self) -> str:
        return self.get("CLUB", "frontend_url", "http://geso-frontend:3000")
    
    @property
    def annual_fee_amount(self) -> float:
        return float(self.get("ANNUAL_FEE", "amount", "1000"))
    
    @property
    def period_type(self) -> str:
        return self.get("ANNUAL_FEE", "period_type", "yearly")
    
    @property
    def prorrate_type(self) -> str:
        return self.get("ANNUAL_FEE", "prorrate_type", "monthly")
    
    @property
    def admin_username(self) -> Optional[str]:
        return self.get("ADMIN", "username", None)
    
    @property
    def admin_email(self) -> Optional[str]:
        return self.get("ADMIN", "email", None)
    
    @property
    def admin_password(self) -> Optional[str]:
        return self.get("ADMIN", "password", None)


# Instancia global de configuración
config = Config()

