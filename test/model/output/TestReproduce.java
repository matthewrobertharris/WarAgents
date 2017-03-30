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

public class TestReproduce extends TestCase {

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
	public void testReproduce_Success_4Free() {
		String file = "resources\\test\\outputMaps\\test_reproduce_success_4free.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == (numAgents + 1));
		assertTrue(agent.getHealth() == (health / 2));
	}
	
	@Test
	public void testReproduce_Success_3Free() {
		String file = "resources\\test\\outputMaps\\test_reproduce_success_3free.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == (numAgents + 1));
		assertTrue(agent.getHealth() == (health / 2));
	}
	
	@Test
	public void testReproduce_Success_2Free() {
		String file = "resources\\test\\outputMaps\\test_reproduce_success_2free.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == (numAgents + 1));
		assertTrue(agent.getHealth() == (health / 2));
	}
	
	@Test
	public void testReproduce_Success_1Free() {
		String file = "resources\\test\\outputMaps\\test_reproduce_success_1free.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == (numAgents + 1)); 
		assertTrue(agent.getHealth() == (health / 2));
	}

	@Test
	public void testReproduce_Fail_Occupied() {
		String file = "resources\\test\\outputMaps\\test_reproduce_fail_occupied.map";
		String error = "Cannot REPRODUCE no extra locations\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == numAgents); 
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testReproduce_Fail_BoundaryOccpied() {
		String file = "resources\\test\\outputMaps\\test_reproduce_fail_boundaryOccupied.map";
		String error = "Cannot REPRODUCE no extra locations\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == numAgents); 
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testReproduce_Fail_Health() {
		String file = "resources\\test\\outputMaps\\test_reproduce_fail_health.map";
		String error = "Cannot REPRODUCE not enough health\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		agent.setHealth(1);
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == numAgents); 
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testReproduce_Fail_TeamSize() {
		String file = "resources\\test\\outputMaps\\test_reproduce_fail_teamSize.map";
		String error = "Cannot REPRODUCE team full\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int numAgents = map.getAllAgents().size();
		int health = agent.getHealth();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.REPRODUCE);
		assertTrue(map.getAllAgents().size() == numAgents); 
		assertTrue(agent.getHealth() == health);
		assertEquals(outContent.toString(), error);
	}
}
