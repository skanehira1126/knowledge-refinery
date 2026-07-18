import mermaid from "https://unpkg.com/mermaid@11/dist/mermaid.esm.min.mjs"

mermaid.initialize({ startOnLoad: false })

document$.subscribe(async () => {
  await mermaid.run({
    nodes: document.querySelectorAll(".mermaid")
  })
})
