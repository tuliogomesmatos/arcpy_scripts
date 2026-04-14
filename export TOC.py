# -*- coding: utf-8 -*-
import arcpy, os, unicodedata

output_folder = u"G:\\Meu Drive\\CLIENTES\CLEBSON - PONTE ALTA\\SIG\\TODOS OS SHAPES"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

mxd = arcpy.mapping.MapDocument("CURRENT")
layers = arcpy.mapping.ListLayers(mxd)

exported = []
skipped = []

def limpar_nome(name):
    if isinstance(name, str):
        name = name.decode("utf-8", errors="replace")
    name = unicodedata.normalize("NFKD", name)
    name = u"".join(c for c in name if not unicodedata.combining(c))
    name = u"".join(c if c.isalnum() or c in u"_-" else u"_" for c in name)
    return name

for layer in layers:
    if layer.isGroupLayer or not layer.isFeatureLayer:
        continue

    safe_name = limpar_nome(layer.name)
    output_path = output_folder + u"\\" + safe_name + u".shp"

    try:
        arcpy.CopyFeatures_management(layer, output_path)
        exported.append(safe_name)
        print("Exportado: " + safe_name.encode("ascii", "replace"))
    except Exception as e:
        skipped.append(safe_name)
        print("Erro: " + safe_name.encode("ascii", "replace") + " - " + str(e))

print("\n" + str(len(exported)) + " exportadas")
print(str(len(skipped)) + " ignoradas")