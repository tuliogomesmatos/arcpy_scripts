import arcpy, os

# Pasta de saida
output_folder = r"C:\Users\tulio\Downloads\shapes"

# Compatível com Python 2.7
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

mxd = arcpy.mapping.MapDocument("CURRENT")
layers = arcpy.mapping.ListLayers(mxd)

exported = []
skipped = []

for layer in layers:
    if layer.isGroupLayer or not layer.isFeatureLayer:
        skipped.append(layer.name)
        continue

    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in layer.name)
    output_path = os.path.join(output_folder, safe_name + ".shp")

    try:
        arcpy.CopyFeatures_management(layer, output_path)
        exported.append(layer.name)
        print("Exportado: " + layer.name)
    except Exception as e:
        skipped.append(layer.name)
        print("Erro em '" + layer.name + "': " + str(e))

print("\n" + str(len(exported)) + " camadas exportadas para: " + output_folder)
print(str(len(skipped)) + " camadas ignoradas")