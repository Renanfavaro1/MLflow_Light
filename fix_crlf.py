with open('server/entrypoint.sh', 'rb') as f:
    content = f.read()
with open('server/entrypoint.sh', 'wb') as f:
    f.write(content.replace(b'\r\n', b'\n'))
print("CRLF removido com sucesso do entrypoint.sh")
