import os
import zipfile

def create_mzp():
    mzp_name = "NoobToolsInstall.mzp"
    if os.path.exists(mzp_name):
        os.remove(mzp_name)
        
    print(f"Building {mzp_name}...")
    with zipfile.ZipFile(mzp_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write("install.ms")
        zf.write("mzp.run")
        if os.path.exists("README.md"):
            zf.write("README.md")
            
        for root, dirs, files in os.walk("src"):
            for f in files:
                # Evitar pycache
                if not f.endswith('.pyc') and '__pycache__' not in root:
                    file_path = os.path.join(root, f)
                    zf.write(file_path)
                    print(f"Added {file_path}")
    
    print(f"Build completed successfully! -> {mzp_name}")

if __name__ == "__main__":
    create_mzp()
