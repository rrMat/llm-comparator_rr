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

DEFAULT_LLM_JUDGE_PROMPT_TEMPLATE = """

### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q) e una risposta di riferimento (GTA).

**Regole di Valutazione:**
1. **A e GTA corrispondono perfettamente nel significato (possono essere formulate diversamente):**
   Verdetto: `Correct`
   Spiegazione: Spiega perché A e GTA corrispondono nel significato.

2. **A e GTA sono diversi:**
   Verdetto: `Wrong`
   Spiegazione: Spiega perché A e GTA differiscono.

3. **A fornisce una risposta incompleta:**
   Verdetto: `Incomplete`
   Spiegazione: Spiega perché A è incomplete.
   
4. **A aggiunge informazioni rispetto a GTA:**
   Verdetto: `Inference`
   Spiegazione: Spiega quali informazioni aggiunge A rispetto a GTA.


**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:
```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['Correct', 'Wrong', 'Incomplete', 'Inference']

---

**Esempi:**

**Esempio 1:**
Q: Che lavoro faceva il richiedente?
A: Cuoco
GTA: lavorava come cuoco

```xml
<result>
  <explanation>A e GTA hanno lo stesso significato.</explanation>
  <verdict>Correct</verdict>
</result>
```

**Esempio 2:**
Q: Qual è il nome della moglie del richiedente?
A: Maria
GTA: Anna

```xml
<result>
  <explanation>A e GTA sono diversi.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 3:**
Q: Perché la commissione non ritiene credibile la dichiarazione?
A: Per via delle contraddizioni.
GTA: Perché il richiedente si contraddice più volte descrivendo la sua fuga, menzionando di essere andato in Grecia, ma al tempo stesso di aver preso un barcone in Libia. 

```xml
<result>
  <explanation>A risponde solo parzialmente alla domanda.</explanation>
  <verdict>Incomplete</verdict>
</result>
```

**Esempio 4:**
Q: Che paesi ha visitato il richiedente?
A: Sudan, Libia, Algeria.
GTA: Sudan, Libia.

```xml
<result>
  <explanation>A aggiunge informazioni rispetto a GTA.</explanation>
  <verdict>Inference</verdict>
</result>
```

---

**Il Tuo Compito:**
Valuta la seguente Q, A e GTA secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

Q: {prompt}
A: {response_a}
GTA: {response_b}

"""

DEFAULT_LLM_JUDGE_WITH_REFERENCE_PROMPT_TEMPLATE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q), una risposta di riferimento (GTA) e il testo (RT) usato per formulare la risposta.

**Regole di Valutazione:**
1. **A contiene una risposta mentre GTA è N/A e, considerando RT, A è inventata:**  
   Verdetto: `Hallucination`  
   Spiegazione: Indica che A fornisce una risposta (compresi "Sì" o "No"), che non ha riscontro in RT.  

2. **A contiene una risposta mentre GTA è N/A e, considerando RT, A è stata inferta da RT ma NON è pertinente alla domanda Q:**  
   Verdetto: `Hallucination`  
   Spiegazione: Indica che A è stata dedotta da RT, ma non risponde direttamente alla domanda Q. Anche se l'informazione è presente in RT, se non è rilevante per la domanda, viene considerata come una distorsione del contesto e quindi classificata come Hallucination.  

3. **A contiene una risposta mentre GTA è N/A e, considerando RT, A è stata inferta da RT ed è pertinente alla domanda Q:**  
   Verdetto: `Inference`  
   Spiegazione: Indica che A fornisce una risposta (compresi "Sì" o "No"), che è stata inferta da RT e risponde direttamente alla domanda Q.  
   
4. **A non è rilevante rispetto alla domanda Q**
    Verdetto: `Hallucination` 
    Spiegazione: A non risponde a Q, indipendentemente da RT la risposta A è frutto di Hallucination. 

**Linea Guida per Differenziare Inference e Hallucination:**
- **Pertinenza alla Domanda:** 
  - Se l'informazione in A è dedotta da RT ma non risponde alla domanda Q, è **Hallucination**.
  - Se l'informazione in A è dedotta da RT e risponde direttamente alla domanda Q, è **Inference**.

- **Traccia nel Testo di Riferimento (RT):**
  - Se A introduce dettagli che non hanno alcuna traccia in RT, è **Hallucination**.
  - Se RT contiene indizi, anche indiretti, che permettono di inferire ragionevolmente la risposta, è **Inference**.


**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:
```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['Hallucination', 'Inference']

---
**Esempi:**

**Esempio 1:**
Q: Che lavoro svolgono o svolgevano i familiari del richiedente?
A: I genitori facevano i pastori, mentre il fratello il fabbro.
GTA: N/A
RT: Il richiedente ricorda di essere nato e cresciuto a Trantimou, Regione di Kayes, Mali, e di aver lavorato come cuoco. Ricorda di avere due fratelli, uno più grande e uno più piccolo, e di non essere sposato né avere figli. Ricorda di aver frequentato la scuola fino all'età di 8 anni. Ricorda di aver vissuto in Gabon per un anno e tre mesi, lavorando come muratore, e di aver litigato con suo fratello per motivi economici. 
```xml
<result>
  <explanation>A non trova riscontro in RT, è stata inventata. </explanation>
  <verdict>Hallucination</verdict>
</result>
```

**Esempio 2:**
Q: Dove dimora il richiedente? 
A: Bamako
GTA: N/A
RT: Poi un giorno sono uscito, avevo fatto delle fotocopie dei miei documenti (carta d'identità, passaporto scaduto). Mentre ero fuori, la polizia è andata a casa di Lori Doli per cercarmi. Se mi avessero visto mi avrebbero ucciso. Poi Lori Doli mi ha chiamato e mi ha spiegato che la polizia mi cercava per uccidermi. A quel punto sono scappato e sono andato a Bamako.

```xml
<result>
  <explanation>A è stata dedotta da RT, viene menzionato il fatto che "sono andato a Bamako", ma non che dimora lì. </explanation>
  <verdict>Inference</verdict>
</result>
```

**Esempio 3:**
Q: Qual è il nome del fratello maggiore del richiedente?
A: Lori Doli
GTA: N/A
RT: Poi un giorno sono uscito, avevo fatto delle fotocopie dei miei documenti (carta d'identità, passaporto scaduto). Mentre ero fuori, la polizia è andata a casa di Lori Doli per cercarmi. Se mi avessero visto mi avrebbero ucciso. Poi Lori Doli mi ha chiamato e mi ha spiegato che la polizia mi cercava per uccidermi. A quel punto sono scappato e sono andato a Bamako.

```xml
<result>
  <explanation>A è stata dedotta da RT, ma non risponde direttamente alla domanda Q. Il testo non specifica che Lori Doli è il fratello maggiore del richiedente, quindi la risposta è fuorviante e non pertinente alla domanda.</explanation>
  <verdict>Hallucination</verdict>
</result>
```

**Esempio 4:**
Q: Perché la commissione ritiene attendibili le circostanze relative al fatto che il commerciante aveva fatto arrestare il richiedente?
A: Il richiedente non ha rivolto alcuna denuncia o richiesta di protezione a nessuna autorità civile o religiosa del suo Paese per contrastare le minacce dello zio.
GTA: N/A
RT: CONSIDERATO che il richiedente dichiara di non essersi rivolto ad alcuna autorità civile o religiosa del suo Paese per contrastare le minacce dello zio.

<result>
  <explanation>A non è pertinente alla domanda Q, poiché parla dello zio invece del commerciante. Nonostante A sia stata dedotta da RT, non risponde direttamente alla domanda Q.</explanation>
  <verdict>Hallucination</verdict>
</result>

---

**Il Tuo Compito:**
Valuta la seguente Q, A, RT e GTA secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

Q: {prompt}
A: {response_a}
RT: {text_reference}
GTA: {response_b}

"""

