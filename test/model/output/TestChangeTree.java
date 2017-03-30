package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestChangeTree extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	@Test
	public void testChangeTree_Success() {
		String file = "resources\\test\\outputMaps\\test_changeTree_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		String treeName = "defend";
		int health = agent.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.CHANGE_TREE);
		assertTrue(map.getAllAgents().size() == numAgents);
		assertTrue(agent.getTree().getName().equals(treeName));
		assertTrue(agent.getHealth() == health);
	}
	
	@Test
	public void testChangeTree_Fail_NoTree() {
		String file = "resources\\test\\outputMaps\\test_changeTree_fail_noTree.map";
		String error = "Cannot CHANGE_TREE because no tree with that name exists\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		String treeName = "change";
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.CHANGE_TREE);
		assertTrue(map.getAllAgents().size() == numAgents);
		assertTrue(agent.getTree().getName().equals(treeName));
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testChangeTree_Fail_AgentNoTree() {
		String file = "resources\\test\\outputMaps\\test_changeTree_fail_agentNoTree.map";
		String error = "Cannot CHANGE_TREE because no tree with that name exists\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		String treeName = "change";
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.CHANGE_TREE);
		assertTrue(map.getAllAgents().size() == numAgents);
		assertTrue(agent.getTree().getName().equals(treeName));
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
}
