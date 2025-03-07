# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Prompt templates for the LLM Comparator script."""


COHERENT_JUDGE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q) e un ragionamento (R). Il tuo compito è determinare se la risposta A è coerente con la domanda Q, tenendo conto del ragionamento R.

---

**Procedura di Valutazione**

1. **Analisi della Domanda (Q):**
   - Identifica chiaramente l'intento principale di Q.
   - Determina quali informazioni specifiche vengono richieste.

2. **Esame della Risposta (A):**
   - Valuta se A affronta direttamente l'intento principale di Q.
   - Verifica che A non confonda concetti correlati ma distinti.
   - Controlla se A è coerente con il contesto di Q.

3. **Esame del Ragionamento (R):**
   - Valuta se R dimostra una comprensione corretta della domanda Q.
   - Conferma che R non introduce errori o confusioni su concetti correlati ma distinti.
   - Assicurati che R supporti adeguatamente la risposta A.

4. **Valutazione Finale:**
   - Se A è coerente con Q e R conferma una comprensione corretta di Q, il verdetto è `Coerente`.
   - Se A sembra inerente a Q ma R mostra una mancata comprensione di Q, il verdetto è `Wrong`.
   - Se A non è coerente con Q, indipendentemente da R, il verdetto è `Wrong`.

---

**Regole di Valutazione**

1. **Coerenza tra A e Q:**
   - Non è necessario che A sia "corretta" per essere considerata coerente. Deve semplicemente affrontare l'intento principale di Q.
   - A deve essere pertinente al contesto di Q e non confondere concetti correlati ma distinti.

2. **Ruolo del Ragionamento (R):**
   - R serve a corroborare A e dimostrare la comprensione della domanda Q.
   - Se R è incoerente o mostra una mancata comprensione di Q, anche una risposta apparentemente corretta A deve essere valutata come `Wrong`.

---

**Formato di Output**

Presenta la tua valutazione nel seguente formato XML:

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
- `Coerente`: La risposta A è coerente con la domanda Q e il ragionamento R conferma una comprensione corretta di Q.
- `Wrong`: La risposta A non è coerente con la domanda Q oppure il ragionamento R mostra una mancata comprensione di Q.

---

**Esempi**

**Esempio 1:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Marco Aurelio
- **R:** L'imperatore romano Marco Aurelio è conosciuto come il saggio.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A fornisce un nome, quindi è inerente.
- Il ragionamento R mostra una comprensione della domanda.

```xml
<result>
  <explanation>A è inerente a Q, e R mostra comprensione della domanda.</explanation>
  <verdict>Coerente</verdict>
</result>
```

**Esempio 2:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Giulio.
- **R:** Il postino si chiamava Giulio.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A fornisce un nome, quindi è inerente.
- Tuttavia, il ragionamento R è completamente fuori contesto e mostra una mancata comprensione della domanda.

```xml
<result>
  <explanation>A sembra inerente a Q, ma R mostra una mancata comprensione della domanda.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 3:**
- **Q:** Come si chiama il primo imperatore romano?
- **A:** Fino alla quarta elementare.
- **R:** Ho insegnato storia a Marco fino alla quarta elementare.

**Analisi:**
- La domanda Q chiede il nome di una persona. La risposta A non fornisce un nome e parla invece di un periodo di tempo, quindi non è coerente con Q.
- Il ragionamento R è completamente fuori contesto.

```xml
<result>
  <explanation>A non è coerente con Q.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 4:**
- **Q:** A Francesco piace il gelato al cioccolato (SI, NO, N/A)?
- **A:** NO
- **R:** Plutone non è più un pianeta dal 2006, l'Unione Astronomica Internazionale, ha deciso di “declassare” Plutone a Pianeta Nano.  

**Analisi:**
- La domanda Q chiede se a Francesco piace il gelato al cioccolato e si aspetta una risposta SI, NO, N/A. La risposta A (NO) è nel fromato corretto.
- Il ragionamento R è completamente fuori contesto, parla di Plutone e del suo status di pianeta. 

```xml
<result>
  <explanation>A non è coerente con Q.</explanation>
  <verdict>Wrong</verdict>
</result>
```

---

**Il Tuo Compito:**
Valuta la seguente Q, A, R secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

- **Q:** {prompt}
- **A:** {response_a}
- **R:** {text_reference}

**Nota finale:**
- Sii obiettivo e limitati alle informazioni fornite. Non fare inferenze o assunzioni aggiuntive.
- Concentrati sulla coerenza tra A e Q, e sul ruolo di R nel dimostrare la comprensione della domanda.
"""



RECURSIVE_JUDGE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Input**
RT: {full_text}
Q: {prompt}
A: {response_a}
GTA: {response_b}


**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q), una risposta di riferimento (GTA) e il testo (RT) usato per formulare la risposta.
Ad ogni riposta possono corrispondere più verdetti, ma a una singola parte può essere assegnato un singolo verdetto.


**Procedura di valutazione**

- Passo 1. Analizzare la Domanda Q:
- - valutare quali informazioni specifiche vengono richieste dalle parti.  

- Passo 2. Esaminare la Risposta A:
- - se possibile scomponi la risposta A in parti A'
- - valuta se le singole parti A' di A forniscono una risposta alla domanda Q
- - Verifica se A o una parte A' corrisponde in significato alla risposta di riferimento GTA.
- - Verifica se A tralascia informazioni contenute nella risposta di riferimento GTA. 

- Passo 3. Analizza il Testo di Riferimento RT:
- - Verificare se A o una parte A' introduce nuove informazioni non presenti nel testo di riferimento RT.
- - Identificare se RT contiene informazioni esplicite o implicite che supportano A'.
- - - Se implicite, determinare se le premesse contenute in RT sono valide e implicano A'.

- Passo 4: Applicare le Regole di Valutazione e eventualmente assegna un verdetto.


**Regole di Valutazione:**
Con A' si intende una parte di A, una domanda A può avere più valutazioni, ma ogni parte A' può avere un singolo label. 

1. **A' e GTA corrispondono perfettamente nel significato (possono essere formulate diversamente):**
   Verdetto: `Correct`
   Spiegazione: Spiega perché A' e GTA corrispondono nel significato.

2. **A' e GTA sono diversi:**
   Verdetto: `Wrong`
   Spiegazione: Spiega perché A' e GTA differiscono.

3. **A fornisce una risposta incompleta:**
   Verdetto: `Incomplete`
   Spiegazione: Spiega quali parti di della risposta di riferimento mancano per rendere A completa.  
      
4. **A' aggiunge informazioni rispetto a GTA che può essere inferta da RT:**
   Verdetto: `Inference`
   Spiegazione: Spiega quali informazioni aggiunge A' rispetto a GTA e da che parte di RT. Perché A' sia considerata 'Inference' l'inferenza deve essere valida. Ovvero le premesse devono implicare la conclusione. 
   
5. **A' aggiunge informazioni non presenti nel teso di riferimento RT.**  
   Verdetto: `Hallucination`  
   Spiegazione: Indica che A' fornisce una risposta che non ha riscontro in RT nè in modo esplicito, nè attraverso inferenza. A' differenza di un Inference l'informazione non può essere inferta dal testo.  


**Linea Guida per Differenziare Inference e Hallucination:**
- **Pertinenza alla Domanda:** 
- - Se l'informazione in A' non è presente nel testo A' è **Hallucination**.
- - Se l'informazione in A' è dedotta da RT e le premesse implicano la conclusione **Inference**.
  
**Line Guida per differenziare fra inferenza valida e inferenza non valida**
- Le premesse presenti in RT implicano A'? Per capirlo bisogna valutare se le premesse sono valide per inferire A'.
- - Se le premesse sono valide A' è **Inference**.
- - Se le premesse non sono valide A' è **Wrong**.

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['Correct', 'Wrong', 'Incomplete', 'Inference', 'Hallucination']


**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:

Analisi:
ANALISI A PASSI QUA

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE PER OGNI VERDETTO QUI.</explanation>
  <verdict>I VERDETTI SELEZIONATI QUI.</verdict>
</result>
```

---

**Esempi:**

**Esempio 1:**
Q: Che lavoro faceva il richiedente?
A: Cuoco
GTA: cuoco
RT: Mario lavora come cuoco da 5 anni presso la cooperativa sociale. Ha una moglie e due figli che vanno a scuola. 

Analisi:

- Passo 1:
La domanda riguarda il lavoro svolto dal richiedente.

- Passo 2:
La risposta è un lavoro ed è pertinente alla domanda. 
La risposta corrisponde a GTA. 
La risposta non tralascia informazioni presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito la risposta (lavora come cuoco). 

- Passo 4: 
Applicando le regole risulta che la risposta A corrisponde a GTA, non tralascia informazioni ed è esplicitamente presente nel testo. Perciò è 'Correct'.  

```xml
<result>
  <explanation>A e GTA hanno lo stesso significato.</explanation>
  <verdict>Correct</verdict>
</result>
```

**Esempio 2:**
Q: Che lingue parla il richiedente?
A: Francese, Tedesco
GTA: Francese
RT: Il richiedente è di madrelingua francese passa spesso le vacanze in germania. 

Analisi:

- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese ed Tedesco.
La due parti di risposta sono due linguee e pertanto pertinenti alla domanda. 
La parte di risposta (Francese) corrisponde a GTA. 
La risposta non tralascia informazioni presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Tedesco) introduce un inferenza non valida, nel testo RT si menziona che il richiedente va in vacanza in germania. Questo premessa non è valida per inferire che il richiedente parli tedesco.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, mentre la parte di risposta Tedesco è un inferenza non valida. Perciò è 'Correct' e 'Wrong'.

```xml
<result>
  <explanation> Francese è Correct, Tedesco è Wrong</explanation>
  <verdict>Correct, Wrong</verdict>
</result>
```

**Esempio 3:**
Q: Che lingue parla il richiedente?
A: Francese, Tedesco
GTA: Francese, Italiano
RT: Il richiedente è di madrelingua francese e vive in Germania. 

Analisi:
- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese ed Tedesco.
La due parti di risposta sono due linguee e pertanto pertinenti alla domanda. 
La parte di risposta (Francese) corrisponde a GTA. 
La risposta tralascia informazioni (Italiano) presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Tedesco) introduce un inferenza valida, nel testo RT si menziona che il richiedente vive in germania. Questo premessa è valida per inferire che il richiedente parlai tedesco.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, la parte di risposta Tedesco è un inferenza valida. Mentre Italiano viene tralasciato. Perciò è 'Correct' e 'Inference' e 'Incomplete'.


```xml
<result>
 <explanation> Francese è Correct, Tedesco è Inference, Italiano manca quindi Incomplete</explanation>
<verdict>Correct, Inference, Incomplete</verdict>
</result>
```

**Esempio 4:**
Q: Che lingue parla il richiedente?
A: Francese, Spagnolo, Polizia
GTA: Francese, Italiano
RT: Il richiedente è di madrelingua francese e vive in Germania. 

Analisi:
- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese, Spagnolo e Polizia.
La due parti di risposta Francese e Spagnolo sono due linguee e pertanto pertinenti alla domanda, mentre polizia non è pertinente. 
La parte di risposta (Francese) corrisponde a GTA. 
La risposta tralascia informazioni (Italiano) presenti in GTA.

- Passo 3:
Il testo contine in modo esplicito parte della risposta (madrelingua francese). 
La risposta (Spagnolo) non è presente nel testo RT in maniera implicita o esplicita. Risulta quini inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese corrisponde a GTA, la parte di risposta Spagnolo è un hallucination. Mentre Italiano viene tralasciato. Perciò è 'Correct' e 'Hallucination' e 'Incomplete'.

  
```xml
<result>
<explanation> Francese è Correct, Spagnolo è Hallucination, Italiano manca quindi Incomplete</explanation>
<verdict>Correct, Hallucination, Incomplete</verdict>
</result>
```

**Esempio 5:**
Q: Che lingue parla il richiedente?
A: Francese
GTA: N/A
RT: Il richiedente lavora come cuoco ed è venuto in italia attraverso la frontiera di Palermo.

Analisi:
- Passo 1:
La domanda riguarda le lingue parlate dal richiedente.

- Passo 2:
La risposta si può scomporre in Francese.
La risposta Francese è una lingua e pertanto pertinente alla domanda.

- Passo 3:
Il testo non contiene infromazioni implicite o esplicite riguardo la domanda.  
La risposta (Francese) non è presente nel testo RT in maniera implicita o esplicita. Risulta quindi inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta Francese è un hallucination. Perciò è 'Hallucination'.

  
```xml
<result>
<explanation> Francese è Hallucination</explanation>
<verdict>Hallucination</verdict>
</result>
```

**Esempio 6:**
Q: Il richiedente parla lo spagnolo (SI, NO, N/A)?
A: NO
GTA: N/A
RT: Il richiedente lavora come cuoco e gli piace arrampicare.

Analisi:
- Passo 1:
La domanda riguarda la lingue parlate dal richiedente ed vuole una risposta nel formato SI, NO, N/A.

- Passo 2:
La risposta si può scomporre in NO.
La risposta NO è nel formato richiesto e pertanto pertinente alla domanda.

- Passo 3:
Il testo non contiene infromazioni implicite o esplicite riguardo la domanda.  
La risposta NO non è presente nel testo RT in maniera implicita o esplicita. Risulta quindi inventata.

- Passo 4: 
Applicando le regole risulta che la parte di risposta NO è un hallucination. Perciò è 'Hallucination'.

  
```xml
<result>
<explanation> NO è Hallucination</explanation>
<verdict>Hallucination</verdict>
</result>
```

**Esempio 7:**
Q: Il richiedente parla lo spagnolo (SI, NO, N/A)?
A: SI
GTA: N/A
RT: Il richiedente vive in Spagna. E gli piace il gelato alla frutta. 

Analisi:
- Passo 1:
La domanda riguarda la lingue parlate dal richiedente ed vuole una risposta nel formato SI, NO, N/A.

- Passo 2:
La risposta si può scomporre in SI.
La risposta SI è nel formato richiesto e pertanto pertinente alla domanda.

- Passo 3:
Il testo contiene infromazioni implicite riguardo la domanda.  
La risposta SI introduce un inferenza valida, nel testo RT si menziona che il richiedente vive in Spagna. Questo premessa è valida per inferire che il richiedente parlai spagnolo.

- Passo 4: 
Applicando le regole risulta che la parte di risposta SI è un inferenza. Perciò è 'Inference'.

  
```xml
<result>
<explanation> Si è Inference</explanation>
<verdict>Inference</verdict>
</result>
```
---

**Note**
Presenta la tua valutazione nel seguente formato analisi + XML:

Analisi:
ANALISI A PASSI QUA

```xml
<result>
  <explanation>LA TUA SPIEGAZIONE PER OGNI VERDETTO QUI.</explanation>
  <verdict>I VERDETTI SELEZIONATI QUI.</verdict>
</result>
```
"""

