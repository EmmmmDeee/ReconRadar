with open('people_finder.py', 'r') as file:
    content = file.read()
    
content = content.replace("if meta_tag and 'content' in meta_tag.attrs:", "if meta_tag and meta_tag.get('content'):")
content = content.replace("return meta_tag['content']", "return meta_tag.get('content')")
content = content.replace("if img and 'src' in img.attrs:", "if img and img.get('src'):")
content = content.replace("return img['src']", "return img.get('src')")

with open('people_finder.py', 'w') as file:
    file.write(content)
    
print("Fixed BeautifulSoup attribute access in people_finder.py")
