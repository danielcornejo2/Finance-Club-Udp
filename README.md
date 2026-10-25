# Monitor de datos macroeconómicos

## Bases de datos 

### Banco de Central de Chile 

Gran parte de las variables utilizadas para la proyección y toma de desiciones de inversión, se basa principalmente en factores macroeconómicos como: 

        · TPM 
        · IPC 
        · IMACEC
        · DESEMPLEO
### FRED 

Por otro lado, respecto al nivel internacional, tendremos que considerar aspectos generalmente de la macreconomía estado unidense. 

        · TASA FED
        · IPC EEUU
        · PRODUCCION INDUSTRIAL
        · PETROLEO BRENT & WTI

### YAHOO FINANCE

En esta sección es relativo la extracción de datos, debido a que será a elección de los equipos los tickers e instrumentos que se llegará a utilizar para realizar la optimización mediante portafolios. 


## Optimización de portafolios 

En esta sección utilizaremos una librería de Python llamada PyPortfolioOp, el cual contiene la utilización de maximización mediante Black-Litterman. 

$$ E[R] = [(\tau \Sigma)^{-1} + P^T \Omega^{-1} P]^{-1} [(\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q] $$

* **$E[R]$**: Vector de retornos esperados ajustados o *posteriores* ($N \times 1$). Estos son los retornos que finalmente se ingresan al optimizador (como `PyPortfolioOpt`).
* **$\tau$**: Escalar de ajuste que representa la incertidumbre sobre el modelo de equilibrio (generalmente un valor pequeño entre 0.01 y 0.05).
* **$\Sigma$**: Matriz de varianzas y covarianzas de los rendimientos de los activos ($N \times N$).
* **$P$**: Matriz de proyección o *Pick Matrix* ($K \times N$). Identifica los activos sobre los cuales el inversor tiene una opinión, donde $K$ es el número de vistas y $N$ el número de activos. Si crees que un activo superará a otro, aquí lo declaras con `1` y `-1`.
* **$\Omega$**: Matriz diagonal de varianzas de las vistas ($K \times K$). Cuantifica la incertidumbre (el margen de error) asignada a cada vista específica, representando la confianza en tus propias proyecciones.
* **$\Pi$**: Vector de retornos implícitos de equilibrio del mercado o *Prior* ($N \times 1$). Se deriva mediante ingeniería inversa a partir de los pesos de capitalización bursátil actuales y el parámetro de aversión al riesgo del mercado.
* **$Q$**: Vector que contiene el valor esperado (absolutos o relativos) de las vistas del inversor ($K \times 1$).
